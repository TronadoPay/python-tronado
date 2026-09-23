"""Client configuration.

:class:`TronadoConfig` holds every tunable knob for the SDK (credentials, base URL,
timeouts, retry policy, default headers). It is a **frozen** dataclass: once built it
cannot be mutated, so a client and its transport can safely hold a shared reference. It
is easy to build, copy (``dataclasses.replace``), log (the API key is redacted in
``repr``), and pass around. The high-level clients accept either keyword arguments *or*
a ready-made ``TronadoConfig``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Dict, Mapping, Optional

from .constants import (
    API_KEY_ENV_VAR,
    API_KEY_HEADER,
    BASE_URL_ENV_VAR,
    DEFAULT_API_VERSION,
    DEFAULT_BACKOFF_FACTOR,
    DEFAULT_BASE_URL,
    DEFAULT_MAX_BACKOFF,
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT,
    DEFAULT_USER_AGENT,
)
from .exceptions import TronadoConfigError


@dataclass(frozen=True)
class TronadoConfig:
    """Immutable configuration for a Tronado client.

    Instances are frozen; build a modified copy with :func:`dataclasses.replace`.

    Args:
        api_key: Tronado API key sent in the ``x-api-key`` header. If ``None``, the
            ``TRONADO_API_KEY`` environment variable is consulted. The price endpoints
            are public, so a key is only required once you call an order endpoint.
        base_url: API base URL (no trailing slash needed). Defaults to the production
            host, overridable via the ``TRONADO_BASE_URL`` environment variable.
        timeout: Total request timeout in seconds.
        max_retries: Maximum retry count for *idempotent* operations. The total number
            of attempts is ``1 + max_retries``.
        backoff_factor: Base multiplier (seconds) for exponential backoff.
        max_backoff: Ceiling for a single backoff sleep (seconds).
        default_version: API version tag used when a caller does not pick one
            explicitly (e.g. ``"v5"``).
        default_headers: Extra headers merged into every request (cannot override the
            API key header). Stored as a read-only mapping (a copy of what you pass).
        user_agent: Value of the ``User-Agent`` header.
        api_key_header: Header name used for the API key. Exposed for forward
            compatibility only; the documented value is ``x-api-key``.

    Raises:
        TronadoConfigError: If the base URL or numeric settings are invalid.
    """

    api_key: Optional[str] = None
    base_url: str = DEFAULT_BASE_URL
    timeout: float = DEFAULT_TIMEOUT
    max_retries: int = DEFAULT_MAX_RETRIES
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR
    max_backoff: float = DEFAULT_MAX_BACKOFF
    default_version: str = DEFAULT_API_VERSION
    default_headers: Mapping[str, str] = field(default_factory=dict)
    user_agent: str = DEFAULT_USER_AGENT
    api_key_header: str = API_KEY_HEADER

    def __post_init__(self) -> None:
        # Frozen dataclass: normalize/derive fields via object.__setattr__.
        api_key = self.api_key if self.api_key is not None else os.getenv(API_KEY_ENV_VAR)
        # A blank key (e.g. an empty env var) is treated as no key at all.
        object.__setattr__(self, "api_key", api_key or None)

        env_base = os.getenv(BASE_URL_ENV_VAR)
        if env_base and self.base_url == DEFAULT_BASE_URL:
            object.__setattr__(self, "base_url", env_base)

        if not isinstance(self.base_url, str) or not self.base_url.lower().startswith(
            ("http://", "https://")
        ):
            raise TronadoConfigError(f"base_url must be an http(s) URL, got {self.base_url!r}.")
        if self.timeout <= 0:
            raise TronadoConfigError("timeout must be a positive number of seconds.")
        if self.max_retries < 0:
            raise TronadoConfigError("max_retries must be >= 0.")
        if self.backoff_factor < 0:
            raise TronadoConfigError("backoff_factor must be >= 0.")

        # Normalize: strip a trailing slash so path joining is unambiguous.
        object.__setattr__(self, "base_url", self.base_url.rstrip("/"))

        # Freeze default_headers: snapshot a copy, then expose a read-only view so the
        # whole config is genuinely immutable (a caller can't mutate it after the fact).
        object.__setattr__(
            self, "default_headers", MappingProxyType(dict(self.default_headers))
        )

    def build_headers(self, *, authenticated: bool = True) -> Dict[str, str]:
        """Build the outgoing header set for a request.

        ``Content-Type: application/json`` is sent on every request, matching the
        documented contract (every request carries a JSON body, at least ``{}``).

        Args:
            authenticated: Whether the endpoint requires the API key. The price
                endpoints are documented as public, so the key is not sent to them.

        Returns:
            A new dict of headers with ``Content-Type``, ``User-Agent``, ``Accept`` and,
            for authenticated endpoints, the API key.

        Raises:
            TronadoConfigError: If ``authenticated`` is true and no API key is configured.
        """
        headers: Dict[str, str] = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": self.user_agent,
        }
        headers.update(self.default_headers)
        if authenticated:
            if not self.api_key:
                raise TronadoConfigError(
                    "A Tronado API key is required for this endpoint. Pass api_key=... or "
                    f"set the {API_KEY_ENV_VAR} environment variable. Request a key from "
                    "https://t.me/TronadoSupp."
                )
            # The API key header is authoritative and cannot be shadowed by default_headers.
            headers[self.api_key_header] = self.api_key
        return headers

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        redacted = "***" if self.api_key else None
        return (
            f"TronadoConfig(api_key={redacted!r}, base_url={self.base_url!r}, "
            f"timeout={self.timeout}, max_retries={self.max_retries}, "
            f"default_version={self.default_version!r})"
        )


__all__ = ["TronadoConfig"]
