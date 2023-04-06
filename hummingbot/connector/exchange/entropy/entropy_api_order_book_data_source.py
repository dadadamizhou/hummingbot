import asyncio
import json
import uuid
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from hummingbot.connector.exchange.entropy import entropy_constants as CONSTANTS, entropy_web_utils as web_utils
from hummingbot.connector.exchange.entropy.entropy_auth import EntropyAuth
from hummingbot.core.data_type.order_book_tracker_data_source import OrderBookTrackerDataSource
from hummingbot.core.web_assistant.connections.data_types import RESTMethod, WSJSONRequest, WSResponse
from hummingbot.core.web_assistant.web_assistants_factory import WebAssistantsFactory
from hummingbot.core.web_assistant.ws_assistant import WSAssistant
from hummingbot.logger import HummingbotLogger

if TYPE_CHECKING:
    from hummingbot.connector.exchange.entropy.entropy_exchange import EntropyExchange


class EntropyAPIOrderBookDataSource(OrderBookTrackerDataSource):
    _logger: Optional[HummingbotLogger] = None

    def __init__(self,
                 trading_pairs: List[str],
                 connector: 'EntropyExchange',
                 api_factory: WebAssistantsFactory,
                 auth: EntropyAuth):
        super().__init__(trading_pairs)
        self._connector = connector
        self._api_factory = api_factory
        self._auth = auth

    async def get_last_traded_prices(self,
                                     trading_pairs: List[str]) -> Dict[str, float]:
        return await self._connector.get_last_traded_prices(trading_pairs=trading_pairs)

    async def _request_order_book_snapshot(self, trading_pair: str) -> Dict[str, Any]:
        """
        Retrieves a copy of the full order book from the exchange, for a particular trading pair.

        :param trading_pair: the trading pair for which the order book will be retrieved

        :return: the response from the exchange (JSON dictionary)
        """
        params = {
            "market": await self._connector.exchange_symbol_associated_to_pair(trading_pair=trading_pair),
            "limit": "100"
        }

        rest_assistant = await self._api_factory.get_rest_assistant()
        data = await rest_assistant.execute_request(
            url=web_utils.public_rest_url(path_url=CONSTANTS.ORDER_BOOK_URL),
            params=params,
            method=RESTMethod.GET,
            throttler_limit_id=CONSTANTS.ORDER_BOOK_URL,
        )

        return data

    async def _connected_websocket_assistant(self) -> WSAssistant:
        """
        Creates an instance of WSAssistant connected to the exchange
        """

        ws: WSAssistant = await self._api_factory.get_ws_assistant()
        await ws.connect(ws_url=CONSTANTS.WSS_URL, message_timeout=CONSTANTS.WS_HEARTBEAT_TIME_INTERVAL)

        payload = self._auth.ws_login_parameters()
        login_request: WSJSONRequest = WSJSONRequest(payload=payload)

        await ws.send(login_request)

        response: WSResponse = await ws.receive()
        message = response.data
        if message.get("type") == "disconnect":
            self.logger().error("Error authenticating the private websocket connection")
            raise IOError("Private websocket connection authentication failed")

        return ws

    async def _subscribe_channels(self, ws: WSAssistant):
        try:
            for trading_pair in self._trading_pairs:
                symbol: str = await self._connector.exchange_symbol_associated_to_pair(trading_pair)
                payload = {
                    "identifier": json.dumps({"handler": CONSTANTS.ORDER_BOOK_HANDLER}),
                    "command": "message",
                    "data": json.dumps({
                        "action": "index",
                        "uuid": str(uuid.uuid4()),
                        "args": {
                            "market_id": symbol
                        }
                    })
                }
                subscribe_orderbook_request: WSJSONRequest = WSJSONRequest(payload=payload)
                payload = {
                    "identifier": json.dumps({"handler": CONSTANTS.TICKER_HANDLER}),
                    "command": "message",
                    "data": json.dumps({
                        "action": "index",
                        "uuid": str(uuid.uuid4()),
                        "args": {
                            "market_id": [symbol]
                        }
                    })
                }
                subscribe_trade_request: WSJSONRequest = WSJSONRequest(payload=payload)
                await ws.send(subscribe_orderbook_request)
                await ws.send(subscribe_trade_request)
            self.logger().info("Subscribed to public order book and trade channels...")
        except asyncio.CancelledError:
            raise
        except Exception:
            self.logger().error(
                "Unexpected error occurred subscribing to order book trading and delta streams...",
                exc_info=True,
            )
            raise
