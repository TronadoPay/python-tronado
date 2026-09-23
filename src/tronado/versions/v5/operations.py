"""v5 operation descriptors.

These constants are the single source of truth for v5 endpoint wiring. Note that only
:data:`GET_ORDER_TOKEN` carries a ``{version}`` segment; every other endpoint lives at
an unversioned root, exactly as documented. The price endpoints are public, so they are
flagged ``requires_auth=False`` and never receive the API key.
"""

from __future__ import annotations

from ...models.order import GetOrderTokenRequest, GetStatusRequest, OrderStatus, OrderTokenData
from ...models.price import (
    DollarConvertRequest,
    DollarPrice,
    GetPriceWithWageRequest,
    PriceWithWage,
    TomanConvertRequest,
    TronConversion,
    TronPrice,
)
from ..base import Operation

GET_ORDER_TOKEN = Operation(
    name="get_order_token",
    method="POST",
    path_template="/api/{version}/GetOrderToken",
    request_model=GetOrderTokenRequest,
    response_model=OrderTokenData,
    idempotent=False,  # creates a transaction — never auto-retried
    envelope=True,
)

GET_STATUS = Operation(
    name="get_status",
    method="POST",
    path_template="/Order/GetStatus",
    request_model=GetStatusRequest,
    response_model=OrderStatus,
    not_found_key="Error",
)

GET_STATUS_BY_PAYMENT_ID = Operation(
    name="get_status_by_payment_id",
    method="POST",
    path_template="/Order/GetStatusByPaymentID",
    request_model=GetStatusRequest,
    response_model=OrderStatus,
    not_found_key="Error",
)

TRON_GET_PRICE_TO_TOMAN = Operation(
    name="tron.get_price_to_toman",
    method="POST",
    path_template="/Tron/GetPriceToToman",
    request_model=None,
    response_model=TronPrice,
    requires_auth=False,
)

TRON_GET_PRICE_WITH_WAGE_TO_TOMAN = Operation(
    name="tron.get_price_with_wage_to_toman",
    method="POST",
    path_template="/Tron/GetPriceWithWageToToman",
    request_model=GetPriceWithWageRequest,
    response_model=PriceWithWage,
    requires_auth=False,
)

TOMAN_CONVERT_TO_TRON = Operation(
    name="toman.convert_to_tron_wage_subtracted",
    method="POST",
    path_template="/Toman/ConvertToTronWageSubtracted",
    request_model=TomanConvertRequest,
    response_model=TronConversion,
    requires_auth=False,
)

# No longer documented (the dollar price lives at /Dollar/GetPriceToToman); kept only
# for the deprecated ``price.toman.get_price_to_toman()``.
TOMAN_GET_PRICE_TO_TOMAN = Operation(
    name="toman.get_price_to_toman",
    method="POST",
    path_template="/Toman/GetPriceToToman",
    request_model=None,
    response_model=DollarPrice,
    requires_auth=False,
)

DOLLAR_CONVERT_TO_TRON = Operation(
    name="dollar.convert_to_tron_wage_subtracted",
    method="POST",
    path_template="/Dollar/ConvertToTronWageSubtracted",
    request_model=DollarConvertRequest,
    response_model=TronConversion,
    requires_auth=False,
)

DOLLAR_GET_PRICE_TO_TOMAN = Operation(
    name="dollar.get_price_to_toman",
    method="POST",
    path_template="/Dollar/GetPriceToToman",
    request_model=None,
    response_model=DollarPrice,
    requires_auth=False,
)


__all__ = [
    "GET_ORDER_TOKEN",
    "GET_STATUS",
    "GET_STATUS_BY_PAYMENT_ID",
    "TRON_GET_PRICE_TO_TOMAN",
    "TRON_GET_PRICE_WITH_WAGE_TO_TOMAN",
    "TOMAN_CONVERT_TO_TRON",
    "TOMAN_GET_PRICE_TO_TOMAN",
    "DOLLAR_CONVERT_TO_TRON",
    "DOLLAR_GET_PRICE_TO_TOMAN",
]
