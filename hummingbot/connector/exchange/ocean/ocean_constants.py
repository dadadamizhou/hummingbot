from hummingbot.core.api_throttler.data_types import RateLimit
from hummingbot.core.data_type.in_flight_order import OrderState

MAX_ORDER_ID_LEN = 32
ORDER_ID_PREFIX = ""

# Base API & WS URLs
REST_URL = "https://api.oceanex.pro/v1"
WSS_URL = "wss://ws.oceanex.cc/ws/v1"

# Public API
TICKERS_URL = "/tickers"
SERVER_TIME_URL = "/timestamp"
ORDER_BOOK_URL = "/order_book"
FEES_TRADING_URL = "/fees/trading"

# Private API
ORDER_PATH_URL = "/orders"
CANCEL_ORDER_PATH_URL = "/order/delete"
ACCOUNTS_PATH_URL = "/members/me"
TRADES_PATH_URL = "/trades"

# wss handler
ORDER_BOOK_HANDLER = "OrderBookHandler"
TICKER_HANDLER = "TickerHandler"

AUTH_HANDLER = "AuthHandler"
ORDER_HISTORY_HANDLER = "OrderHistoryHandler"

WS_HEARTBEAT_TIME_INTERVAL = 30

SIDE_BUY = 'buy'
SIDE_SELL = 'sell'

ONE_MINUTE = 60
ONE_SECOND = 1
ONE_DAY = 86400

MAX_REQUEST = 5000

ORDER_STATUS = {
    "wait": OrderState.OPEN,
    "wait_trigger": OrderState.OPEN,
    "cancel": OrderState.CANCELED,
    "done": OrderState.FILLED,
    "cancelling": OrderState.PENDING_CANCEL,
    "incomplete": OrderState.PARTIALLY_FILLED
}

RATE_LIMITS = [
    RateLimit(limit_id=TICKERS_URL, limit=MAX_REQUEST, time_interval=ONE_SECOND),
    RateLimit(limit_id=SERVER_TIME_URL, limit=MAX_REQUEST, time_interval=ONE_SECOND),
    RateLimit(limit_id=ORDER_BOOK_URL, limit=MAX_REQUEST, time_interval=ONE_SECOND),
    RateLimit(limit_id=ORDER_PATH_URL, limit=MAX_REQUEST, time_interval=ONE_SECOND),
    RateLimit(limit_id=CANCEL_ORDER_PATH_URL, limit=MAX_REQUEST, time_interval=ONE_SECOND),
    RateLimit(limit_id=ACCOUNTS_PATH_URL, limit=MAX_REQUEST, time_interval=ONE_SECOND),
    RateLimit(limit_id=TRADES_PATH_URL, limit=MAX_REQUEST, time_interval=ONE_SECOND),
]
