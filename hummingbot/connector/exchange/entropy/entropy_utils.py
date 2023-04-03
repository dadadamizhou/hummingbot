from decimal import Decimal

from pydantic import Field, SecretStr

from hummingbot.client.config.config_data_types import BaseConnectorConfigMap, ClientFieldData
from hummingbot.core.data_type.trade_fee import TradeFeeSchema

CENTRALIZED = True
EXAMPLE_PAIR = "BTC-USDT"


DEFAULT_FEES = TradeFeeSchema(
    maker_percent_fee_decimal=Decimal("0.001"),
    taker_percent_fee_decimal=Decimal("0.001"),
)


class EntropyConfigMap(BaseConnectorConfigMap):
    connector: str = Field(default="entropy", client_data=None)
    entropy_uid: SecretStr = Field(
        default=...,
        client_data=ClientFieldData(
            prompt=lambda cm: "Enter your Entropy uid",
            is_secure=True,
            is_connect_key=True,
            prompt_on_new=True,
        )
    )
    entropy_apikey_id: SecretStr = Field(
        default=...,
        client_data=ClientFieldData(
            prompt=lambda cm: "Enter your Entropy apikey id",
            is_secure=True,
            is_connect_key=True,
            prompt_on_new=True,
        )
    )

    entropy_private_key: SecretStr = Field(
        default=...,
        client_data=ClientFieldData(
            prompt=lambda cm: "Enter your Entropy private key (Base64)",
            is_secure=True,
            is_connect_key=True,
            prompt_on_new=True,
        )
    )

    class Config:
        title = "entropy"


KEYS = EntropyConfigMap.construct()
