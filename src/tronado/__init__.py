"""Tronado — a production-grade, version-aware Python SDK for the Tronado Public API.

Quickstart::

    from tronado import TronadoClient

    with TronadoClient(api_key="sk-...") as tron:
        price = tron.price.tron.get_price_to_toman()
        order = tron.order.get_order_token(
            payment_id="inv-1001",
            wallet_address="TXYZ...",
            tron_amount="12.123456",
            callback_url="https://your-domain.com/payment/callback",
        )
        print(order.full_payment_url)

See :mod:`tronado.webhook` for verifying inbound IPN and dispute callbacks.
"""

from __future__ import annotations

from .client import AsyncTronadoClient, TronadoClient
from .config import TronadoConfig
from .constants import (
    API_KEY_HEADER,
    DEFAULT_API_VERSION,
    DEFAULT_BASE_URL,
    PAYMENT_PAGE_URL_TEMPLATE,
    SDK_VERSION,
    WEBHOOK_SIGNATURE_HEADER,
    DisputeEvent,
    DisputeOutcome,
    DisputeTypeCode,
    OrderStatusCode,
)
from .exceptions import (
    InvalidSignatureError,
    OrderNotFoundError,
    TronadoAPIError,
    TronadoAuthenticationError,
    TronadoConfigError,
    TronadoConnectionError,
    TronadoError,
    TronadoRateLimitError,
    TronadoServerError,
    TronadoTimeoutError,
    TronadoValidationError,
    TronadoWebhookError,
)
from .models import (
    ApiEnvelope,
    CallbackPayload,
    DisputeCallbackPayload,
    DollarConvertRequest,
    DollarPrice,
    GetOrderTokenRequest,
    GetPriceWithWageRequest,
    GetStatusRequest,
    OrderStatus,
    OrderTokenData,
    PriceWithWage,
    TomanConvertRequest,
    TronConversion,
    TronPrice,
)
from .versions import available_versions
from .webhook import (
    compute_signature,
    construct_dispute_event,
    construct_event,
    parse_callback,
    parse_dispute_callback,
    verify_signature,
)

__version__ = SDK_VERSION

__all__ = [
    "__version__",
    # clients & config
    "TronadoClient",
    "AsyncTronadoClient",
    "TronadoConfig",
    # constants
    "OrderStatusCode",
    "DisputeEvent",
    "DisputeTypeCode",
    "DisputeOutcome",
    "DEFAULT_BASE_URL",
    "DEFAULT_API_VERSION",
    "API_KEY_HEADER",
    "WEBHOOK_SIGNATURE_HEADER",
    "PAYMENT_PAGE_URL_TEMPLATE",
    "available_versions",
    # webhook helpers
    "verify_signature",
    "compute_signature",
    "parse_callback",
    "construct_event",
    "parse_dispute_callback",
    "construct_dispute_event",
    # models
    "ApiEnvelope",
    "CallbackPayload",
    "DisputeCallbackPayload",
    "GetOrderTokenRequest",
    "GetStatusRequest",
    "OrderTokenData",
    "OrderStatus",
    "GetPriceWithWageRequest",
    "TomanConvertRequest",
    "DollarConvertRequest",
    "TronPrice",
    "PriceWithWage",
    "TronConversion",
    "DollarPrice",
    # exceptions
    "TronadoError",
    "TronadoConfigError",
    "TronadoConnectionError",
    "TronadoTimeoutError",
    "TronadoAPIError",
    "TronadoAuthenticationError",
    "TronadoRateLimitError",
    "OrderNotFoundError",
    "TronadoValidationError",
    "TronadoServerError",
    "TronadoWebhookError",
    "InvalidSignatureError",
]
