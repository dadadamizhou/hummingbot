import asyncio
import time
import uuid
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from hummingbot.connector.exchange.ocean import ocean_constants as CONSTANTS, ocean_web_utils as web_utils
from hummingbot.connector.exchange.ocean.ocean_auth import OceanAuth
from hummingbot.connector.exchange.ocean.ocean_order_book import OceanOrderBook
from hummingbot.core.data_type.order_book_message import OrderBookMessage
from hummingbot.core.data_type.order_book_tracker_data_source import OrderBookTrackerDataSource
from hummingbot.core.web_assistant.connections.data_types import RESTMethod, WSJSONRequest
from hummingbot.core.web_assistant.web_assistants_factory import WebAssistantsFactory
from hummingbot.core.web_assistant.ws_assistant import WSAssistant
from hummingbot.logger import HummingbotLogger

if TYPE_CHECKING:
    from hummingbot.connector.exchange.ocean.ocean_exchange import OceanExchange


class OceanAPIOrderBookDataSource(OrderBookTrackerDataSource):
    _logger: Optional[HummingbotLogger] = None

    def __init__(self,
                 trading_pairs: List[str],
                 connector: 'OceanExchange',
                 api_factory: WebAssistantsFactory,
                 auth: OceanAuth):
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

    async def _order_book_snapshot(self, trading_pair: str) -> OrderBookMessage:
        snapshot: Dict[str, Any] = await self._request_order_book_snapshot(trading_pair)
        snapshot_data = snapshot["data"]
        snapshot_msg: OrderBookMessage = OceanOrderBook.snapshot_message_from_exchange(
            snapshot_data,
            snapshot_data["timestamp"],
            metadata={"trading_pair": trading_pair}
        )
        return snapshot_msg

    async def _connected_websocket_assistant(self) -> WSAssistant:
        """
        Creates an instance of WSAssistant connected to the exchange
        """
        ws: WSAssistant = await self._api_factory.get_ws_assistant()
        await ws.connect(ws_url=CONSTANTS.WSS_URL, message_timeout=CONSTANTS.WS_HEARTBEAT_TIME_INTERVAL)
        return ws

    async def _subscribe_channels(self, ws: WSAssistant):
        try:
            for trading_pair in self._trading_pairs:
                symbol: str = await self._connector.exchange_symbol_associated_to_pair(trading_pair)
                payload = {
                    "identifier": {"handler": CONSTANTS.ORDER_BOOK_HANDLER},
                    "command": "message",
                    "data": {
                        "action": "index",
                        "uuid": str(uuid.uuid4()),
                        "args": {
                            "market": symbol
                        }
                    }
                }
                subscribe_orderbook_request: WSJSONRequest = WSJSONRequest(payload=payload)
                payload = {
                    "identifier": {"handler": CONSTANTS.TICKER_HANDLER},
                    "command": "message",
                    "data": {
                        "action": "index",
                        "uuid": str(uuid.uuid4()),
                        "args": {
                            "markets": [symbol]
                        }
                    }
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

    async def _parse_trade_message(self, raw_message: Dict[str, Any], message_queue: asyncio.Queue):
        for symbol in raw_message["message"]["data"]:
            trading_pair = await self._connector.trading_pair_associated_to_exchange_symbol(symbol=symbol)
            trade_message = OceanOrderBook.trade_message_from_exchange(
                raw_message["message"]["data"][symbol], {"trading_pair": trading_pair})
            message_queue.put_nowait(trade_message)

    async def _parse_order_book_snapshot_message(self, raw_message: Dict[str, Any], message_queue: asyncio.Queue):
        trading_pair: str = await self._connector.trading_pair_associated_to_exchange_symbol('btcusdt')
        order_book_data = raw_message["message"]["data"]
        timestamp = time.time()
        order_book_message: OrderBookMessage = OceanOrderBook.snapshot_message_from_exchange(
            order_book_data,
            timestamp,
            metadata={"trading_pair": trading_pair}
        )
        message_queue.put_nowait(order_book_message)

    def _channel_originating_message(self, event_message: Dict[str, Any]) -> str:
        channel = ""
        if "identifier" in event_message:
            event_channel = event_message["identifier"]["handler"]
            if event_channel == CONSTANTS.TICKER_HANDLER:
                channel = self._trade_messages_queue_key
            if event_channel == CONSTANTS.ORDER_BOOK_HANDLER:
                channel = self._snapshot_messages_queue_key
        return channel
