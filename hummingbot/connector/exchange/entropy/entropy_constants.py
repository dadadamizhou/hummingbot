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

WS_HEARTBEAT_TIME_INTERVAL = 30

SIDE_BUY = 'buy'
SIDE_SELL = 'sell'

ONE_MINUTE = 60
ONE_SECOND = 1
ONE_DAY = 86400

MAX_REQUEST = 5000

# Order States
ORDER_STATUS = {
    -1: OrderState.CANCELED,
    0: OrderState.OPEN,
    1: OrderState.PARTIALLY_FILLED,
    2: OrderState.FILLED,
    3: OrderState.CANCELED,  # Partially Filled and Cancelled
    4: OrderState.PENDING_CANCEL
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
