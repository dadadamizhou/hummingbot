from decimal import Decimal
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from bidict import bidict

from hummingbot.connector.exchange.entropy import entropy_constants as CONSTANTS, entropy_web_utils as web_utils
from hummingbot.connector.exchange.entropy.entropy_api_order_book_data_source import EntropyAPIOrderBookDataSource
from hummingbot.connector.exchange.entropy.entropy_api_user_stream_data_source import EntropyAPIUserStreamDataSource
from hummingbot.connector.exchange.entropy.entropy_auth import EntropyAuth
from hummingbot.connector.exchange_py_base import ExchangePyBase
from hummingbot.connector.trading_rule import TradingRule
from hummingbot.connector.utils import combine_to_hb_trading_pair
from hummingbot.core.data_type.common import OrderType, TradeType
from hummingbot.core.data_type.in_flight_order import InFlightOrder, OrderUpdate, TradeUpdate
from hummingbot.core.data_type.order_book_tracker_data_source import OrderBookTrackerDataSource
from hummingbot.core.data_type.trade_fee import TradeFeeBase
from hummingbot.core.data_type.user_stream_tracker_data_source import UserStreamTrackerDataSource
from hummingbot.core.utils.estimate_fee import build_trade_fee
from hummingbot.core.web_assistant.web_assistants_factory import WebAssistantsFactory

if TYPE_CHECKING:
    from hummingbot.client.config.config_helpers import ClientConfigAdapter


class EntropyExchange(ExchangePyBase):
    web_utils = web_utils

    def __init__(
            self,
            client_config_map: "ClientConfigAdapter",
            entropy_uid: str,
            entropy_apikey_id: str,
            entropy_private_key: str,
            trading_pairs: Optional[List[str]] = None,
            trading_required: bool = True,
    ):
        self.entropy_uid = entropy_uid
        self.entropy_apikey_id = entropy_apikey_id
        self.entropy_private_key = entropy_private_key
        self._trading_pairs = trading_pairs or []
        self._trading_required = trading_required
        super().__init__(client_config_map)

    @staticmethod
    def entropy_order_type(order_type: OrderType) -> str:
        return order_type.name.lower()

    @property
    def authenticator(self):
        return EntropyAuth(
            uid=self.entropy_uid, apikey_id=self.entropy_apikey_id, private_key=self.entropy_private_key
        )

    @property
    def name(self):
        return "entropy"

    @property
    def rate_limits_rules(self):
        return CONSTANTS.RATE_LIMITS

    @property
    def domain(self):
        return ""

    @property
    def client_order_id_max_length(self):
        return CONSTANTS.MAX_ORDER_ID_LEN

    @property
    def client_order_id_prefix(self):
        return CONSTANTS.ORDER_ID_PREFIX

    @property
    def trading_rules_request_path(self):
        return CONSTANTS.TICKERS

    @property
    def trading_pairs_request_path(self):
        return CONSTANTS.TICKERS

    @property
    def check_network_request_path(self):
        return CONSTANTS.SERVER_TIME_URL

    @property
    def trading_pairs(self):
        return self._trading_pairs

    @property
    def is_cancel_request_in_exchange_synchronous(self) -> bool:
        return True

    @property
    def is_trading_required(self) -> bool:
        return self._trading_required

    def supported_order_types(self):
        return [OrderType.LIMIT, OrderType.MAKER]

    def _is_request_exception_related_to_time_synchronizer(self, request_exception: Exception):
        # Exchange does not have a particular error for incorrect timestamps
        return False

    def _create_web_assistants_factory(self) -> WebAssistantsFactory:
        return web_utils.build_api_factory(
            throttler=self._throttler,
            time_synchronizer=self._time_synchronizer,
            auth=self._auth)

    def _create_order_book_data_source(self) -> OrderBookTrackerDataSource:
        return EntropyAPIOrderBookDataSource(
            trading_pairs=self._trading_pairs,
            connector=self,
            api_factory=self._web_assistants_factory,
            auth=self._auth
        )

    def _create_user_stream_data_source(self) -> UserStreamTrackerDataSource:
        return EntropyAPIUserStreamDataSource(
            trading_pairs=self._trading_pairs,
            connector=self,
            api_factory=self._web_assistants_factory,
            auth=self._auth,
        )

    def _initialize_trading_pair_symbols_from_exchange_info(self, exchange_info: Dict[str, Any]):
        mapping = bidict()
        symbol_list: List[Dict[str, Any]] = exchange_info.get("data")
        for symbol in symbol_list:
            mapping[symbol] = combine_to_hb_trading_pair(base=symbol_list[symbol]["base_unit"].upper(),
                                                         quote=symbol_list["symbol"]["quote_unit"].upper())
        self._set_trading_pair_symbol_map(mapping)

    async def _format_trading_rules(self, exchange_info_dict: Dict[str, Any]) -> List[TradingRule]:
        retval: List[TradingRule] = []
        symbol_list: List[Dict[str, Any]] = exchange_info_dict.get("data")
        for symbol in symbol_list:
            try:
                trading_pair = await self.trading_pair_associated_to_exchange_symbol(symbol=symbol_list)
                retval.append(
                    TradingRule(
                        trading_pair=trading_pair,
                        min_order_size=Decimal(0),  # xxx
                        min_base_amount_increment=Decimal(0),  # xxx
                        min_price_increment=Decimal(0),  # xxx
                    )
                )
            except Exception:
                self.logger().exception(f"Error parsing trading pair rule {symbol}. Skipping.")
        return retval

    async def _place_order(self,
                           order_id: str,
                           trading_pair: str,
                           amount: Decimal,
                           trade_type: TradeType,
                           order_type: OrderType,
                           price: Decimal,
                           **kwargs) -> Tuple[str, float]:
        type_str = EntropyExchange.entropy_order_type(order_type)
        side_str = CONSTANTS.SIDE_BUY if trade_type is TradeType.BUY else CONSTANTS.SIDE_SELL
        symbol = await self.exchange_symbol_associated_to_pair(trading_pair=trading_pair)
        api_params = {"market": symbol,
                      "side": side_str,
                      "volume": amount,
                      "price": price,
                      "ord_type": type_str}

        response = await self._api_post(
            path_url=CONSTANTS.ORDER_PATH_URL,
            data=api_params,
            is_auth_required=True)
        if response.get("code") != 0:
            err_code: int = response.get("code")
            err_msg: str = response.get("message")
            raise ValueError(f"Error submitting order: {err_code} {err_msg} Response: {response}")
        o_id = str(response["data"]["id"])
        transact_time = response["data"]["created_on"]
        return o_id, transact_time

    async def _place_cancel(self, order_id: str, tracked_order: InFlightOrder) -> bool:
        exchange_order_id = await tracked_order.get_exchange_order_id()
        data = {
            "id": int(exchange_order_id),
        }
        response = await self._api_post(
            path_url=CONSTANTS.CANCEL_ORDER_PATH_URL,
            data=data,
            is_auth_required=True,
        )
        if response.get("code") != 0:
            err_code: int = response.get("code")
            err_msg: str = response.get("message")
            raise ValueError(f"Error submitting order: {err_code} {err_msg} Response: {response}")
        return True

    def _get_fee(
            self,
            base_currency: str,
            quote_currency: str,
            order_type: OrderType,
            order_side: TradeType,
            amount: Decimal,
            price: Decimal,
            is_maker: Optional[bool] = None,
    ) -> TradeFeeBase:
        is_maker = is_maker or (order_type in (OrderType.LIMIT_MAKER, OrderType.LIMIT))
        return build_trade_fee(
            exchange=self.name,
            is_maker=is_maker,
            base_currency=base_currency,
            quote_currency=quote_currency,
            order_type=order_type,
            order_side=order_side,
            amount=amount,
            price=price,
        )

    async def _get_last_traded_price(self, trading_pair: str) -> float:
        params = {
            "market": await self.exchange_symbol_associated_to_pair(trading_pair=trading_pair),
            "limit": 1
        }

        response = await self._api_post(
            path_url=CONSTANTS.TRADES_PATH_URL,
            data=params)
        ticker_data: Optional[List[Dict[str, Any]]] = response.get("data", None)
        if ticker_data:
            return float(ticker_data[0]["price"])

    async def _update_balances(self):
        local_asset_names = set(self._account_balances.keys())
        remote_asset_names = set()

        response = await self._api_post(path_url=CONSTANTS.ACCOUNTS_PATH_URL, is_auth_required=True)

        balances = response.get("data", None)
        for balance_entry in balances["accounts"]:
            asset_name = balance_entry["currency"].upper()
            free_balance = Decimal(balance_entry["balance"])
            total_balance = Decimal(balance_entry["balance"]) + Decimal(balance_entry["locked"])
            self._account_available_balances[asset_name] = free_balance
            self._account_balances[asset_name] = total_balance
            remote_asset_names.add(asset_name)
        asset_names_to_remove = local_asset_names.difference(remote_asset_names)
        for asset_name in asset_names_to_remove:
            del self._account_available_balances[asset_name]
            del self._account_balances[asset_name]

    async def _request_order_status(self, tracked_order: InFlightOrder) -> OrderUpdate:
        exchange_order_id = await tracked_order.get_exchange_order_id()
        response = await self._api_get(
            path_url=CONSTANTS.ORDER_PATH_URL,
            params={"ids": [exchange_order_id]},
            is_auth_required=True)

        if response.get("code") != 0:
            err_code: int = response.get("code")
            err_msg: str = response.get("message")
            raise ValueError(f"Error submitting order: {err_code} {err_msg} Response: {response}")
        updated_order_data = response.get("data")[0]
        new_state = CONSTANTS.ORDER_STATE[updated_order_data["status"]]

        order_update = OrderUpdate(
            client_order_id=tracked_order.client_order_id,
            exchange_order_id=str(updated_order_data["id"]),
            trading_pair=tracked_order.trading_pair,
            update_timestamp=self.current_timestamp,
            new_state=new_state,
        )
        return order_update

    async def _update_trading_fees(self):
        """
        Update fees information from the exchange
        """
        pass

    async def _all_trade_updates_for_order(self, order: InFlightOrder) -> List[TradeUpdate]:
        pass

    async def _user_stream_event_listener(self):
        pass
