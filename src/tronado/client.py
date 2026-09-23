"""High-level synchronous and asynchronous Tronado clients.

These are the primary entry points. A client owns a :class:`TronadoConfig` and a
transport, lazily builds version bundles via the registry, and exposes convenience
accessors (``order``, ``price``) for the configured default version plus explicit
version pinning (``client.version("v5")`` / ``client.v5``).

Synchronous::

    from tronado import TronadoClient
    with TronadoClient(api_key="...") as tron:
        price = tron.price.tron.get_price_to_toman()

Asynchronous::

    from tronado import AsyncTronadoClient
    async with AsyncTronadoClient(api_key="...") as tron:
        price = await tron.price.tron.get_price_to_toman()
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Mapping, Optional, cast

import httpx

from ._http.async_transport import AsyncTransport
from ._http.sync_transport import SyncTransport
from .config import TronadoConfig
from .constants import (
    DEFAULT_API_VERSION,
    DEFAULT_BACKOFF_FACTOR,
    DEFAULT_BASE_URL,
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT,
    DEFAULT_USER_AGENT,
)
from .versions import build_async_version, build_sync_version
from .versions.base import BaseVersion
from .versions.v5 import V5AsyncVersion, V5SyncVersion

if TYPE_CHECKING:
    from .versions.v5.resources import (
        AsyncOrderResource,
        AsyncPriceNamespace,
        OrderResource,
        PriceNamespace,
    )


def _build_config(
    api_key: Optional[str],
    base_url: str,
    timeout: float,
    max_retries: int,
    backoff_factor: float,
    default_version: str,
    default_headers: Optional[Mapping[str, str]],
    user_agent: Optional[str],
) -> TronadoConfig:
    return TronadoConfig(
        api_key=api_key,
        base_url=base_url,
        timeout=timeout,
        max_retries=max_retries,
        backoff_factor=backoff_factor,
        default_version=default_version,
        default_headers=dict(default_headers or {}),
        user_agent=user_agent if user_agent is not None else DEFAULT_USER_AGENT,
    )


class TronadoClient:
    """Synchronous Tronado API client.

    Args:
        api_key: API key for the ``x-api-key`` header. Falls back to ``TRONADO_API_KEY``.
            Only the order endpoints need it; the price endpoints are public.
        base_url: Base URL (defaults to production; ``TRONADO_BASE_URL`` honoured).
        timeout: Per-request timeout in seconds.
        max_retries: Maximum retries for idempotent operations.
        backoff_factor: Exponential-backoff base multiplier (seconds).
        default_version: Version tag used by the ``order``/``price`` shortcuts.
        default_headers: Extra headers added to every request.
        user_agent: Override the ``User-Agent`` header.
        config: A ready-made :class:`TronadoConfig`. If given, all other settings are
            ignored.
        http_client: Optional pre-built :class:`httpx.Client` (its lifecycle is yours).

    Example:
        >>> with TronadoClient(api_key="sk-...") as tron:
        ...     token = tron.order.get_order_token(
        ...         payment_id="inv-1",
        ...         wallet_address="T...",
        ...         tron_amount="12.34",
        ...         callback_url="https://example.com/cb",
        ...     )
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
        default_version: str = DEFAULT_API_VERSION,
        default_headers: Optional[Mapping[str, str]] = None,
        user_agent: Optional[str] = None,
        config: Optional[TronadoConfig] = None,
        http_client: Optional[httpx.Client] = None,
    ) -> None:
        self._config = config or _build_config(
            api_key,
            base_url,
            timeout,
            max_retries,
            backoff_factor,
            default_version,
            default_headers,
            user_agent,
        )
        self._transport = SyncTransport(self._config, http_client=http_client)
        self._version_cache: dict[str, BaseVersion] = {}

    @property
    def config(self) -> TronadoConfig:
        """The active configuration."""
        return self._config

    def version(self, tag: Optional[str] = None) -> BaseVersion:
        """Return the resource bundle for ``tag`` (default: the configured version)."""
        tag = tag or self._config.default_version
        if tag not in self._version_cache:
            self._version_cache[tag] = build_sync_version(tag, self._transport)
        return self._version_cache[tag]

    @property
    def v5(self) -> V5SyncVersion:
        """The v5 resource bundle (explicit version pin)."""
        return cast(V5SyncVersion, self.version("v5"))

    @property
    def order(self) -> OrderResource:
        """Order resource of the default version."""
        return cast(V5SyncVersion, self.version()).order

    @property
    def price(self) -> PriceNamespace:
        """Price namespace of the default version (``.tron``/``.toman``/``.dollar``)."""
        return cast(V5SyncVersion, self.version()).price

    def close(self) -> None:
        """Close the underlying HTTP client (if owned by this client)."""
        self._transport.close()

    def __enter__(self) -> TronadoClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


class AsyncTronadoClient:
    """Asynchronous Tronado API client (mirror of :class:`TronadoClient`).

    Example:
        >>> async with AsyncTronadoClient(api_key="sk-...") as tron:
        ...     price = await tron.price.tron.get_price_to_toman()
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
        default_version: str = DEFAULT_API_VERSION,
        default_headers: Optional[Mapping[str, str]] = None,
        user_agent: Optional[str] = None,
        config: Optional[TronadoConfig] = None,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self._config = config or _build_config(
            api_key,
            base_url,
            timeout,
            max_retries,
            backoff_factor,
            default_version,
            default_headers,
            user_agent,
        )
        self._transport = AsyncTransport(self._config, http_client=http_client)
        self._version_cache: dict[str, BaseVersion] = {}

    @property
    def config(self) -> TronadoConfig:
        """The active configuration."""
        return self._config

    def version(self, tag: Optional[str] = None) -> BaseVersion:
        """Return the async resource bundle for ``tag`` (default: configured version)."""
        tag = tag or self._config.default_version
        if tag not in self._version_cache:
            self._version_cache[tag] = build_async_version(tag, self._transport)
        return self._version_cache[tag]

    @property
    def v5(self) -> V5AsyncVersion:
        """The async v5 resource bundle (explicit version pin)."""
        return cast(V5AsyncVersion, self.version("v5"))

    @property
    def order(self) -> AsyncOrderResource:
        """Async order resource of the default version."""
        return cast(V5AsyncVersion, self.version()).order

    @property
    def price(self) -> AsyncPriceNamespace:
        """Async price namespace of the default version."""
        return cast(V5AsyncVersion, self.version()).price

    async def aclose(self) -> None:
        """Close the underlying async HTTP client (if owned by this client)."""
        await self._transport.aclose()

    async def __aenter__(self) -> AsyncTronadoClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()


__all__ = ["TronadoClient", "AsyncTronadoClient"]
