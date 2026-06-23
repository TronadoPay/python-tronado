"""Request and response models for the price/conversion resources."""

from __future__ import annotations

from pydantic import Field

from .base import TronadoModel, TronDecimal

# --------------------------------------------------------------------------- requests


class GetPriceWithWageRequest(TronadoModel):
    """Body for ``POST /Tron/GetPriceWithWageToToman``.

    Attributes:
        request_code: Code provisioned by Tronado support.
        wallet_address: Destination wallet address.
        tron_amount: TRX amount to price.
    """

    request_code: str = Field(alias="RequestCode")
    wallet_address: str = Field(alias="WalletAddress")
    tron_amount: TronDecimal = Field(alias="TronAmount")


class TomanConvertRequest(TronadoModel):
    """Body for ``POST /Toman/ConvertToTronWageSubtracted``.

    Attributes:
        toman: Amount in Toman to convert.
        wallet: Destination wallet address.
    """

    toman: int = Field(alias="Toman")
    wallet: str = Field(alias="Wallet")


class DollarConvertRequest(TronadoModel):
    """Body for ``POST /Dollar/ConvertToTronWageSubtracted``.

    Attributes:
        dollar: Amount in USD to convert.
        wallet: Destination wallet address.
    """

    dollar: TronDecimal = Field(alias="Dollar")
    wallet: str = Field(alias="Wallet")


# -------------------------------------------------------------------------- responses


class TronPrice(TronadoModel):
    """Response of ``GET /Tron/GetPriceToToman``.

    Attributes:
        tron_price_toman: Price of 1 TRX in Toman (not Rial).
        tron_price_dollar: Price of 1 TRX in USD.
    """

    tron_price_toman: int = Field(alias="TronPriceToman")
    tron_price_dollar: TronDecimal = Field(alias="TronPriceDollar")


class PriceWithWage(TronadoModel):
    """Response of ``POST /Tron/GetPriceWithWageToToman``.

    Attributes:
        actual_amount_toman: Toman value of the requested TRX, excluding wage.
        amount_with_wage_toman: Toman value including the wage/fee.
    """

    actual_amount_toman: int = Field(alias="ActualAmountToman")
    amount_with_wage_toman: int = Field(alias="AmountWithWageToman")


class TronConversion(TronadoModel):
    """Response of the ``ConvertToTronWageSubtracted`` endpoints.

    Attributes:
        tron_amount: Equivalent TRX amount (wage not included).
        tron_sun_amount: Same amount expressed in Sun (1 TRX = 1,000,000 Sun).
    """

    tron_amount: TronDecimal = Field(alias="TronAmount")
    tron_sun_amount: TronDecimal = Field(alias="TronSunAmount")


class DollarPrice(TronadoModel):
    """Response of the ``GetPriceToToman`` dollar-price endpoints.

    Attributes:
        dollar_price: Price of 1 USD in Toman.
    """

    dollar_price: int = Field(alias="DollarPrice")


__all__ = [
    "GetPriceWithWageRequest",
    "TomanConvertRequest",
    "DollarConvertRequest",
    "TronPrice",
    "PriceWithWage",
    "TronConversion",
    "DollarPrice",
]
