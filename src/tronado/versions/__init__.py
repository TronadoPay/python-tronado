"""API version registry.

Maps a version tag (e.g. ``"v5"``) to its concrete sync/async resource bundles. To add
a new version later, implement ``versions/v6/`` and register it in :data:`_REGISTRY` —
no other module needs to change.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Dict, Tuple

from ..exceptions import TronadoConfigError
from .base import BaseVersion, Operation
from .v5 import V5AsyncVersion, V5SyncVersion

if TYPE_CHECKING:
    from .._http.async_transport import AsyncTransport
    from .._http.sync_transport import SyncTransport

    #: A factory that builds a version bundle from a transport.
    SyncVersionFactory = Callable[[SyncTransport], BaseVersion]
    AsyncVersionFactory = Callable[[AsyncTransport], BaseVersion]

#: tag -> (sync version factory, async version factory)
_REGISTRY: Dict[str, Tuple[SyncVersionFactory, AsyncVersionFactory]] = {
    "v5": (V5SyncVersion, V5AsyncVersion),
}


def available_versions() -> Tuple[str, ...]:
    """Return the tuple of supported version tags."""
    return tuple(sorted(_REGISTRY))


def _resolve(tag: str) -> Tuple[SyncVersionFactory, AsyncVersionFactory]:
    try:
        return _REGISTRY[tag]
    except KeyError:
        supported = ", ".join(available_versions())
        raise TronadoConfigError(
            f"Unsupported API version {tag!r}. Supported versions: {supported}."
        ) from None


def build_sync_version(tag: str, transport: SyncTransport) -> BaseVersion:
    """Instantiate the synchronous resource bundle for ``tag``."""
    sync_factory, _ = _resolve(tag)
    return sync_factory(transport)


def build_async_version(tag: str, transport: AsyncTransport) -> BaseVersion:
    """Instantiate the asynchronous resource bundle for ``tag``."""
    _, async_factory = _resolve(tag)
    return async_factory(transport)


__all__ = [
    "Operation",
    "BaseVersion",
    "available_versions",
    "build_sync_version",
    "build_async_version",
]
