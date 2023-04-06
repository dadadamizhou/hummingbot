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


class OceanConfigMap(BaseConnectorConfigMap):
    connector: str = Field(default="ocean", client_data=None)
    ocean_uid: SecretStr = Field(
        default=...,
        client_data=ClientFieldData(
            prompt=lambda cm: "Enter your Ocean uid",
            is_secure=True,
            is_connect_key=True,
            prompt_on_new=True,
        )
    )
    ocean_apikey_id: SecretStr = Field(
        default=...,
        client_data=ClientFieldData(
            prompt=lambda cm: "Enter your Ocean apikey id",
            is_secure=True,
            is_connect_key=True,
            prompt_on_new=True,
        )
    )

    ocean_private_key: SecretStr = Field(
        default=...,
        client_data=ClientFieldData(
            prompt=lambda cm: "Enter your Ocean private key (Base64)",
            is_secure=True,
            is_connect_key=True,
            prompt_on_new=True,
        )
    )

    class Config:
        title = "ocean"


KEYS = OceanConfigMap.construct()
