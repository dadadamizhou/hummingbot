import asyncio
import uuid
from typing import TYPE_CHECKING, List, Optional

from hummingbot.connector.exchange.ocean import ocean_constants as CONSTANTS
from hummingbot.connector.exchange.ocean.ocean_auth import OceanAuth
from hummingbot.core.data_type.in_flight_order import OrderState
from hummingbot.core.data_type.user_stream_tracker_data_source import UserStreamTrackerDataSource
from hummingbot.core.web_assistant.connections.data_types import WSJSONRequest, WSResponse
from hummingbot.core.web_assistant.web_assistants_factory import WebAssistantsFactory
from hummingbot.core.web_assistant.ws_assistant import WSAssistant
from hummingbot.logger import HummingbotLogger

if TYPE_CHECKING:
    from hummingbot.connector.exchange.ocean.ocean_exchange import OceanExchange


class OceanAPIUserStreamDataSource(UserStreamTrackerDataSource):
    LISTEN_KEY_KEEP_ALIVE_INTERVAL = 1800  # Recommended to Ping/Update listen key to keep connection alive
    HEARTBEAT_TIME_INTERVAL = 30.0

    _logger: Optional[HummingbotLogger] = None

    def __init__(self,
                 trading_pairs: List[str],
                 connector: 'OceanExchange',
                 api_factory: WebAssistantsFactory,
                 auth: OceanAuth):
        super().__init__()
        self._auth = auth
        self._current_listen_key = None
        self._api_factory = api_factory
        self._connector = connector

    async def _connected_websocket_assistant(self) -> WSAssistant:
        """
        Creates an instance of WSAssistant connected to the exchange
        """
        ws: WSAssistant = await self._api_factory.get_ws_assistant()
        await ws.connect(ws_url=CONSTANTS.WSS_URL, message_timeout=CONSTANTS.WS_HEARTBEAT_TIME_INTERVAL)

        payload = self._auth.ws_login_parameters()
        login_request: WSJSONRequest = WSJSONRequest(payload=payload)

        async with self._api_factory.throttler.execute_task(limit_id=CONSTANTS.AUTH_HANDLER):
            await ws.send(login_request)

        response: WSResponse = await ws.receive()
        message = response.data
        if message.get("type") == "disconnect":
            self.logger().error("Error authenticating the private websocket connection")
            raise IOError("Private websocket connection authentication failed")

        return ws

    async def listen_for_user_stream(self, output: asyncio.Queue):
        """
        Connects to the user private channel in the exchange using a websocket connection. With the established
        connection listens to

        all balance events and order updates provided by the exchange, and stores them in the
        output queue

        :param output: the queue to use to store the received messages
        """
        while True:
            try:
                self._ws_assistant = await self._connected_websocket_assistant()
                await self._subscribe_channels(websocket_assistant=self._ws_assistant, queue=output)
                # await self._send_ping(websocket_assistant=self._ws_assistant)  # to update last_recv_timestamp
                # await self._process_websocket_messages(websocket_assistant=self._ws_assistant, queue=output)
            except asyncio.CancelledError:
                raise
            except ConnectionError as connection_exception:
                self.logger().warning(f"The websocket connection was closed ({connection_exception})")
            except Exception:
                self.logger().exception("Unexpected error while listening to user stream. Retrying after 5 seconds...")
                await self._sleep(1.0)
            finally:
                await self._on_user_stream_interruption(websocket_assistant=self._ws_assistant)
                self._ws_assistant = None

    async def _subscribe_channels(self, websocket_assistant: WSAssistant, queue: asyncio.Queue):
        while True:
            cancel_order = []
            for order in self._connector._order_tracker.all_orders.values():
                if order.current_state == OrderState.FILLED:
                    continue
                # 暂时预留一下看看 被取消的订单 是否在这里更新一下数据
                if order.current_state == OrderState.CANCELED:
                    if order.exchange_order_id in cancel_order:
                        continue
                    cancel_order.append(order.exchange_order_id)
                request_uuid = str(order.client_order_id) + "_" + str(uuid.uuid4())
                if order.current_state == CONSTANTS.ORDER_STATUS["cancel"]:
                    handler = CONSTANTS.ORDER_HISTORY_HANDLER
                else:
                    handler = CONSTANTS.ORDER_HANDLER
                payload = {
                    "identifier": {"handler": handler},
                    "command": "message",
                    "data": {
                        "action": "show",
                        "uuid": request_uuid,
                        "args": {
                            "id": order.exchange_order_id
                        }
                    }
                }
                subscribe_order_request: WSJSONRequest = WSJSONRequest(payload=payload)
                await websocket_assistant.send(subscribe_order_request)
            while True:
                try:
                    await asyncio.wait_for(self._process_ws_messages(ws=websocket_assistant, queue=queue), timeout=1)
                except asyncio.TimeoutError:
                    break
            # 更新一下余额
            await self._connector._update_balances()
            await self._sleep(1)

    async def _process_ws_messages(self, ws: WSAssistant, queue: asyncio.Queue):
        response = await ws.receive()
        message = response.data
        if "type" in message and message['type'] == "ping":
            pong_request = WSJSONRequest(payload={"command": "pong"})
            await ws.send(request=pong_request)
        if "identifier" in message:
            if message["identifier"]["handler"] in [CONSTANTS.ORDER_HANDLER, CONSTANTS.ORDER_HISTORY_HANDLER]:
                queue.put_nowait(message)
