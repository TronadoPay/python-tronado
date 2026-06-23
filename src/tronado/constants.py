"""Project-wide constants and documented enumerations.

Everything here is taken directly from the Tronado Public API documentation. We do
**not** invent values that the documentation does not define (see ``OrderStatusCode``).
"""

from __future__ import annotations

from enum import IntEnum

#: SDK version, also used to build the default ``User-Agent`` header.
SDK_VERSION = "0.1.0"

#: Default ``User-Agent`` header value.
DEFAULT_USER_AGENT = f"tronado-python/{SDK_VERSION}"

#: Default production base URL (no trailing slash).
DEFAULT_BASE_URL = "https://bot.tronado.cloud"

#: Default API version tag. The version segment is placed in the URL path as
#: ``/api/{version}/...`` and currently only applies to ``GetOrderToken``.
DEFAULT_API_VERSION = "v5"

#: Total request timeout, in seconds.
DEFAULT_TIMEOUT = 30.0

#: Maximum number of *retries* (so ``1 + DEFAULT_MAX_RETRIES`` total attempts) for
#: idempotent operations.
DEFAULT_MAX_RETRIES = 3

#: Base multiplier for exponential backoff between retries, in seconds.
DEFAULT_BACKOFF_FACTOR = 0.5

#: Upper bound for a single backoff sleep, in seconds.
DEFAULT_MAX_BACKOFF = 30.0

#: HTTP header name carrying the API key. The documented scheme is a bare key in
#: this header — **not** ``Authorization: Bearer``.
API_KEY_HEADER = "x-api-key"

#: Environment variable consulted when no API key is passed explicitly.
API_KEY_ENV_VAR = "TRONADO_API_KEY"

#: Environment variable consulted when no base URL is passed explicitly.
BASE_URL_ENV_VAR = "TRONADO_BASE_URL"

#: Header that Tronado sets on every IPN/webhook callback. Its value is the
#: lowercase hex HMAC-SHA512 of the raw request body keyed with your IPN signing key.
WEBHOOK_SIGNATURE_HEADER = "X-Tronado-Sig"


class OrderStatusCode(IntEnum):
    """Documented Tronado order-status identifiers.

    The public documentation only defines a single status value explicitly. Treat any
    other ``OrderStatusID`` returned by the API as an unknown/forward-compatible value
    rather than assuming a meaning for it.
    """

    PAYMENT_ACCEPTED = 30
    """A successful payment. Equivalent to ``IsPaid == True``."""


__all__ = [
    "SDK_VERSION",
    "DEFAULT_USER_AGENT",
    "DEFAULT_BASE_URL",
    "DEFAULT_API_VERSION",
    "DEFAULT_TIMEOUT",
    "DEFAULT_MAX_RETRIES",
    "DEFAULT_BACKOFF_FACTOR",
    "DEFAULT_MAX_BACKOFF",
    "API_KEY_HEADER",
    "API_KEY_ENV_VAR",
    "BASE_URL_ENV_VAR",
    "WEBHOOK_SIGNATURE_HEADER",
    "OrderStatusCode",
]
