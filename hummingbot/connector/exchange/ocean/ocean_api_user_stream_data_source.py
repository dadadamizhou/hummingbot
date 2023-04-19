import asyncio
from typing import TYPE_CHECKING, List, Optional

from hummingbot.connector.exchange.ocean import ocean_constants as CONSTANTS
from hummingbot.connector.exchange.ocean.ocean_auth import OceanAuth
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

        self._listen_key_initialized_event: asyncio.Event = asyncio.Event()
        self._last_listen_key_ping_ts = 0

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

    async def _subscribe_channels(self, websocket_assistant: WSAssistant):
        """
                Subscribes to the trade events and diff orders events through the provided websocket connection.

                Binance does not require any channel subscription.

                :param websocket_assistant: the websocket assistant used to connect to the exchange
                """
        pass

    async def _process_websocket_messages(self, websocket_assistant: WSAssistant, queue: asyncio.Queue):
        async for ws_response in websocket_assistant.iter_messages():
            print(ws_response)
            message = ws_response.data
            if "type" in message and message['type'] == "ping":
                pong_request = WSJSONRequest(payload={"command": "pong"})
                await websocket_assistant.send(request=pong_request)
