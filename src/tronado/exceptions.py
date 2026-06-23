"""Exception hierarchy for the Tronado SDK.

All errors raised by this library derive from :class:`TronadoError`, so callers can
catch everything with a single ``except TronadoError``. More specific subclasses let
you react to particular failure modes (authentication, rate limiting, a missing order,
transport problems, webhook signature failures, …).

::

    TronadoError
    ├── TronadoConfigError
    ├── TronadoConnectionError
    │   └── TronadoTimeoutError
    ├── TronadoAPIError
    │   ├── TronadoAuthenticationError
    │   ├── TronadoRateLimitError
    │   ├── OrderNotFoundError
    │   ├── TronadoValidationError
    │   └── TronadoServerError
    └── TronadoWebhookError
        └── InvalidSignatureError
"""

from __future__ import annotations

from typing import Any, Optional


class TronadoError(Exception):
    """Base class for every error raised by the SDK."""


class TronadoConfigError(TronadoError):
    """The client was configured incorrectly (e.g. missing API key, bad base URL)."""


class TronadoConnectionError(TronadoError):
    """A network-level failure occurred before a usable HTTP response was received."""

    def __init__(self, message: str, *, cause: Optional[BaseException] = None) -> None:
        super().__init__(message)
        if cause is not None:
            # Preserve the original exception for tracebacks / debugging.
            self.__cause__ = cause


class TronadoTimeoutError(TronadoConnectionError):
    """The request exceeded the configured timeout."""


class TronadoAPIError(TronadoError):
    """The API returned an error response.

    Attributes:
        message: Human-readable error message (from the API when available).
        status_code: HTTP status code, if one was received.
        code: Tronado business ``Code`` from the response envelope, if present.
        response: The decoded JSON body (or raw text) returned by the API, if any.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        code: Optional[int] = None,
        response: Any = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code
        self.response = response

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        parts = [self.message]
        if self.status_code is not None:
            parts.append(f"HTTP {self.status_code}")
        if self.code is not None:
            parts.append(f"Code {self.code}")
        return " | ".join(parts)


class TronadoAuthenticationError(TronadoAPIError):
    """The API key was missing, malformed, or rejected (HTTP 401 / ``Code == -1``)."""


class TronadoRateLimitError(TronadoAPIError):
    """A rate limit or per-user transaction limit was hit (HTTP 429)."""


class OrderNotFoundError(TronadoAPIError):
    """No order matched the supplied identifier.

    Tronado signals this as **HTTP 200** with a body of
    ``{"Error": "No order found with this txid"}``; the SDK surfaces it as this
    exception so callers can handle a miss explicitly instead of inspecting payloads.
    """


class TronadoValidationError(TronadoAPIError):
    """The API rejected the request as invalid, or returned ``IsSuccessful == false``."""


class TronadoServerError(TronadoAPIError):
    """The API returned a 5xx response (retried for idempotent operations)."""


class TronadoWebhookError(TronadoError):
    """Base class for inbound IPN/webhook processing errors."""


class InvalidSignatureError(TronadoWebhookError):
    """The ``X-Tronado-Sig`` HMAC-SHA512 signature did not match the raw body."""


__all__ = [
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
