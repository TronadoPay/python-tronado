"""v5 resource facades (synchronous and asynchronous).

Each resource method is a thin, fully-typed facade: it builds a request model and
delegates to ``transport.invoke``. All retry/error/serialization *logic* lives in the
transport and the pure helpers, so the sync and async variants below differ only by
``await`` — there is no duplicated behaviour, only duplicated (trivial) signatures.

The ``price`` resources call public endpoints: they work without an API key.
"""

from __future__ import annotations

import warnings
from decimal import Decimal
from typing import TYPE_CHECKING

from ...models.base import AmountInput
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
from . import operations as ops

if TYPE_CHECKING:
    # Imported for typing only to avoid a runtime import cycle (the transport imports
    # ``versions.base``). The high-level clients inject the concrete transport.
    from ..._http.async_transport import AsyncTransport
    from ..._http.sync_transport import SyncTransport


def _decimal(value: AmountInput) -> Decimal:
    """Coerce an amount input to ``Decimal`` via ``str`` (avoids binary-float error)."""
    return value if isinstance(value, Decimal) else Decimal(str(value))


def _check_wage(percentage: int) -> int:
    """Validate the documented 0–100 range for ``wage_from_business_percentage``.

    Raises:
        ValueError: If ``percentage`` is outside the inclusive 0–100 range.
    """
    if not 0 <= percentage <= 100:
        raise ValueError(
            "wage_from_business_percentage must be between 0 and 100 (inclusive), "
            f"got {percentage!r}"
        )
    return percentage


def _warn_toman_price_deprecated() -> None:
    warnings.warn(
        "price.toman.get_price_to_toman() calls /Toman/GetPriceToToman, which is no longer "
        "documented; use price.dollar.get_price_to_toman() instead (same response).",
        DeprecationWarning,
        stacklevel=3,
    )


# =============================================================================== sync


class OrderResource:
    """Synchronous ``Order`` operations."""

    def __init__(self, transport: SyncTransport, version: str) -> None:
        self._transport = transport
        self._version = version

    def get_order_token(
        self,
        *,
        payment_id: str,
        wallet_address: str,
        tron_amount: AmountInput,
        callback_url: str,
        wage_from_business_percentage: int = 0,
    ) -> OrderTokenData:
        """Create a new transaction and obtain its payment token.

        Args:
            payment_id: Your application's unique payment identifier.
            wallet_address: Destination TRON wallet address.
            tron_amount: Invoice amount in TRX (use the price endpoints to compute it).
            callback_url: HTTPS URL Tronado will POST payment results to. Its domain
                must be registered with Tronado support beforehand; otherwise no
                callback is sent at all.
            wage_from_business_percentage: Share of the fee (0–100) the business
                absorbs. ``0`` (default) adds the whole fee on top of the user's
                payment; ``100`` subtracts it from your share. It also decides which
                webhook amount to credit (see
                :class:`~tronado.models.webhook.CallbackPayload`).

        Returns:
            The order token, payment URLs and estimated Toman amount. Use
            :attr:`~tronado.models.order.OrderTokenData.payment_page_url` for a button
            in your own bot.

        Note:
            This operation creates a transaction and is therefore **not** retried
            automatically, even on network failure, to avoid duplicate orders.
        """
        request = GetOrderTokenRequest(
            payment_id=payment_id,
            wallet_address=wallet_address,
            tron_amount=_decimal(tron_amount),
            callback_url=callback_url,
        )
        return self._transport.invoke(
            ops.GET_ORDER_TOKEN,
            request,
            version=self._version,
            query={"wageFromBusinessPercentage": _check_wage(wage_from_business_percentage)},
        )

    def get_status(self, *, id: str) -> OrderStatus:
        """Look up an order by Tronado OrderId, ``TrndOrderID_{id}`` or TXID.

        Raises:
            OrderNotFoundError: If no order matches ``id``.
        """
        return self._transport.invoke(
            ops.GET_STATUS, GetStatusRequest(id=id), version=self._version
        )

    def get_status_by_payment_id(self, *, id: str) -> OrderStatus:
        """Look up an order by your application's ``PaymentID``.

        Raises:
            OrderNotFoundError: If no order matches ``id``.
        """
        return self._transport.invoke(
            ops.GET_STATUS_BY_PAYMENT_ID, GetStatusRequest(id=id), version=self._version
        )


class TronPriceResource:
    """Synchronous ``Tron`` price operations."""

    def __init__(self, transport: SyncTransport, version: str) -> None:
        self._transport = transport
        self._version = version

    def get_price_to_toman(self) -> TronPrice:
        """Get the current TRX price in Toman and USD (no input)."""
        return self._transport.invoke(ops.TRON_GET_PRICE_TO_TOMAN, version=self._version)

    def get_price_with_wage_to_toman(
        self, *, request_code: str, wallet_address: str, tron_amount: AmountInput
    ) -> PriceWithWage:
        """Convert a TRX amount to Toman, with and without the wage/fee.

        Authenticated by ``request_code`` (provisioned by Tronado support), not the API key.
        """
        request = GetPriceWithWageRequest(
            request_code=request_code,
            wallet_address=wallet_address,
            tron_amount=_decimal(tron_amount),
        )
        return self._transport.invoke(
            ops.TRON_GET_PRICE_WITH_WAGE_TO_TOMAN, request, version=self._version
        )


class TomanPriceResource:
    """Synchronous ``Toman`` operations."""

    def __init__(self, transport: SyncTransport, version: str) -> None:
        self._transport = transport
        self._version = version

    def convert_to_tron_wage_subtracted(self, *, toman: int, wallet: str) -> TronConversion:
        """Convert a Toman amount to TRX (wage not included)."""
        request = TomanConvertRequest(toman=toman, wallet=wallet)
        return self._transport.invoke(ops.TOMAN_CONVERT_TO_TRON, request, version=self._version)

    def get_price_to_toman(self) -> DollarPrice:
        """Get the current USD price in Toman.

        .. deprecated:: 0.2.0
            ``/Toman/GetPriceToToman`` is no longer documented. Use
            :meth:`DollarPriceResource.get_price_to_toman`, which returns the same data.
        """
        _warn_toman_price_deprecated()
        return self._transport.invoke(ops.TOMAN_GET_PRICE_TO_TOMAN, version=self._version)


class DollarPriceResource:
    """Synchronous ``Dollar`` operations."""

    def __init__(self, transport: SyncTransport, version: str) -> None:
        self._transport = transport
        self._version = version

    def convert_to_tron_wage_subtracted(
        self, *, dollar: AmountInput, wallet: str
    ) -> TronConversion:
        """Convert a USD amount to TRX (wage not included)."""
        request = DollarConvertRequest(dollar=_decimal(dollar), wallet=wallet)
        return self._transport.invoke(ops.DOLLAR_CONVERT_TO_TRON, request, version=self._version)

    def get_price_to_toman(self) -> DollarPrice:
        """Get the current USD price in Toman (no input)."""
        return self._transport.invoke(ops.DOLLAR_GET_PRICE_TO_TOMAN, version=self._version)


class PriceNamespace:
    """Groups the synchronous price resources: ``.tron``, ``.toman``, ``.dollar``."""

    def __init__(self, transport: SyncTransport, version: str) -> None:
        self.tron = TronPriceResource(transport, version)
        self.toman = TomanPriceResource(transport, version)
        self.dollar = DollarPriceResource(transport, version)


# ============================================================================== async


class AsyncOrderResource:
    """Asynchronous ``Order`` operations (mirror of :class:`OrderResource`)."""

    def __init__(self, transport: AsyncTransport, version: str) -> None:
        self._transport = transport
        self._version = version

    async def get_order_token(
        self,
        *,
        payment_id: str,
        wallet_address: str,
        tron_amount: AmountInput,
        callback_url: str,
        wage_from_business_percentage: int = 0,
    ) -> OrderTokenData:
        """Create a transaction and obtain its payment token.

        See :meth:`OrderResource.get_order_token` for full parameter documentation.
        """
        request = GetOrderTokenRequest(
            payment_id=payment_id,
            wallet_address=wallet_address,
            tron_amount=_decimal(tron_amount),
            callback_url=callback_url,
        )
        return await self._transport.invoke(
            ops.GET_ORDER_TOKEN,
            request,
            version=self._version,
            query={"wageFromBusinessPercentage": _check_wage(wage_from_business_percentage)},
        )

    async def get_status(self, *, id: str) -> OrderStatus:
        """Look up an order by OrderId/``TrndOrderID_{id}``/TXID."""
        return await self._transport.invoke(
            ops.GET_STATUS, GetStatusRequest(id=id), version=self._version
        )

    async def get_status_by_payment_id(self, *, id: str) -> OrderStatus:
        """Look up an order by your application's ``PaymentID``."""
        return await self._transport.invoke(
            ops.GET_STATUS_BY_PAYMENT_ID, GetStatusRequest(id=id), version=self._version
        )


class AsyncTronPriceResource:
    """Asynchronous ``Tron`` price operations."""

    def __init__(self, transport: AsyncTransport, version: str) -> None:
        self._transport = transport
        self._version = version

    async def get_price_to_toman(self) -> TronPrice:
        """Get the current TRX price in Toman and USD."""
        return await self._transport.invoke(ops.TRON_GET_PRICE_TO_TOMAN, version=self._version)

    async def get_price_with_wage_to_toman(
        self, *, request_code: str, wallet_address: str, tron_amount: AmountInput
    ) -> PriceWithWage:
        """Convert a TRX amount to Toman, with and without the wage."""
        request = GetPriceWithWageRequest(
            request_code=request_code,
            wallet_address=wallet_address,
            tron_amount=_decimal(tron_amount),
        )
        return await self._transport.invoke(
            ops.TRON_GET_PRICE_WITH_WAGE_TO_TOMAN, request, version=self._version
        )


class AsyncTomanPriceResource:
    """Asynchronous ``Toman`` operations."""

    def __init__(self, transport: AsyncTransport, version: str) -> None:
        self._transport = transport
        self._version = version

    async def convert_to_tron_wage_subtracted(self, *, toman: int, wallet: str) -> TronConversion:
        """Convert a Toman amount to TRX (wage not included)."""
        request = TomanConvertRequest(toman=toman, wallet=wallet)
        return await self._transport.invoke(
            ops.TOMAN_CONVERT_TO_TRON, request, version=self._version
        )

    async def get_price_to_toman(self) -> DollarPrice:
        """Get the current USD price in Toman.

        .. deprecated:: 0.2.0
            Use :meth:`AsyncDollarPriceResource.get_price_to_toman` instead.
        """
        _warn_toman_price_deprecated()
        return await self._transport.invoke(ops.TOMAN_GET_PRICE_TO_TOMAN, version=self._version)


class AsyncDollarPriceResource:
    """Asynchronous ``Dollar`` operations."""

    def __init__(self, transport: AsyncTransport, version: str) -> None:
        self._transport = transport
        self._version = version

    async def convert_to_tron_wage_subtracted(
        self, *, dollar: AmountInput, wallet: str
    ) -> TronConversion:
        """Convert a USD amount to TRX (wage not included)."""
        request = DollarConvertRequest(dollar=_decimal(dollar), wallet=wallet)
        return await self._transport.invoke(
            ops.DOLLAR_CONVERT_TO_TRON, request, version=self._version
        )

    async def get_price_to_toman(self) -> DollarPrice:
        """Get the current USD price in Toman."""
        return await self._transport.invoke(ops.DOLLAR_GET_PRICE_TO_TOMAN, version=self._version)


class AsyncPriceNamespace:
    """Groups the asynchronous price resources: ``.tron``, ``.toman``, ``.dollar``."""

    def __init__(self, transport: AsyncTransport, version: str) -> None:
        self.tron = AsyncTronPriceResource(transport, version)
        self.toman = AsyncTomanPriceResource(transport, version)
        self.dollar = AsyncDollarPriceResource(transport, version)


__all__ = [
    "OrderResource",
    "TronPriceResource",
    "TomanPriceResource",
    "DollarPriceResource",
    "PriceNamespace",
    "AsyncOrderResource",
    "AsyncTronPriceResource",
    "AsyncTomanPriceResource",
    "AsyncDollarPriceResource",
    "AsyncPriceNamespace",
]
