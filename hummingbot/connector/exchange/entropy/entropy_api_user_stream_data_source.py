import asyncio
from typing import TYPE_CHECKING, List, Optional

from hummingbot.connector.exchange.entropy.entropy_auth import EntropyAuth
from hummingbot.core.data_type.user_stream_tracker_data_source import UserStreamTrackerDataSource
from hummingbot.core.web_assistant.web_assistants_factory import WebAssistantsFactory
from hummingbot.logger import HummingbotLogger

if TYPE_CHECKING:
    from hummingbot.connector.exchange.entropy.entropy_exchange import EntropyExchange


class EntropyAPIUserStreamDataSource(UserStreamTrackerDataSource):
    LISTEN_KEY_KEEP_ALIVE_INTERVAL = 1800  # Recommended to Ping/Update listen key to keep connection alive
    HEARTBEAT_TIME_INTERVAL = 30.0

    _logger: Optional[HummingbotLogger] = None

    def __init__(self,
                 trading_pairs: List[str],
                 connector: 'EntropyExchange',
                 api_factory: WebAssistantsFactory,
                 auth: EntropyAuth):
        super().__init__()
        self._auth = auth
        self._current_listen_key = None
        self._api_factory = api_factory

        self._listen_key_initialized_event: asyncio.Event = asyncio.Event()
        self._last_listen_key_ping_ts = 0
