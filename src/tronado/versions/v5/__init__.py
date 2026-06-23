"""API version **v5** binding.

Recommended version. Highlights vs. earlier versions:

* The webhook adds ``UserPaidTomanAmount`` and ``TomanAmountWithoutWage``.
* Every callback is signed with HMAC-SHA512 in the ``X-Tronado-Sig`` header.
* A callback is sent on *every* status change, not only on a successful payment.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..base import BaseVersion
from .resources import (
    AsyncOrderResource,
    AsyncPriceNamespace,
    OrderResource,
    PriceNamespace,
)

if TYPE_CHECKING:
    from ..._http.async_transport import AsyncTransport
    from ..._http.sync_transport import SyncTransport

#: Version tag for this binding.
VERSION_TAG = "v5"


class V5SyncVersion(BaseVersion):
    """Synchronous v5 resource bundle.

    Attributes:
        order: Order operations (create token, status lookups).
        price: Price/conversion namespace (``.tron``, ``.toman``, ``.dollar``).
    """

    tag = VERSION_TAG

    def __init__(self, transport: SyncTransport) -> None:
        self.order = OrderResource(transport, self.tag)
        self.price = PriceNamespace(transport, self.tag)


class V5AsyncVersion(BaseVersion):
    """Asynchronous v5 resource bundle (mirror of :class:`V5SyncVersion`)."""

    tag = VERSION_TAG

    def __init__(self, transport: AsyncTransport) -> None:
        self.order = AsyncOrderResource(transport, self.tag)
        self.price = AsyncPriceNamespace(transport, self.tag)


__all__ = ["VERSION_TAG", "V5SyncVersion", "V5AsyncVersion"]
