"""Model for the inbound IPN/webhook callback payload (Tronado → your server)."""

from __future__ import annotations

from typing import Optional, Tuple

from pydantic import AliasChoices, Field

from ..constants import OrderStatusCode
from .base import FlexibleDateTime, TronadoModel, TronDecimal


class CallbackPayload(TronadoModel):
    """Body that Tronado POSTs to your ``CallbackUrl`` on every order status change.

    One callback is sent per status change (not only on success). De-duplicate using
    :attr:`dedup_key`. To charge the end user, prefer :attr:`user_paid_toman_amount`
    (the amount the user actually paid, including wage) over :attr:`tron_amount` (your
    net receipt).

    Note:
        The v5 webhook payload uses ``PaymentId`` (lower ``d``) whereas the status
        endpoints use ``PaymentID``. :attr:`payment_id` accepts **either** spelling on
        input (and serializes back to ``PaymentId``), so it is robust to that drift.

    Attributes:
        unique_code: Tronado unique transaction code (the GUID token in v5).
        payment_id: Your application's payment id.
        user_telegram_id: Telegram id of the payer.
        wallet: Destination wallet.
        hash: On-chain TXID (or ``TrndOrderID_{id}``).
        tron_amount: Net TRX delivered to you after wage handling.
        actual_tron_amount: Original TRX amount before any adjustment.
        user_paid_toman_amount: (v5) Toman the user actually paid — use this to charge.
        toman_amount_without_wage: (v5) Base Toman amount excluding wage.
        order_status_id: Numeric status (``30`` == ``PaymentAccepted``).
        order_status_title: Human-readable status title.
        is_paid: Whether the payment succeeded.
        payment_date: Status timestamp.
    """

    unique_code: Optional[str] = Field(default=None, alias="UniqueCode")
    payment_id: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("PaymentId", "PaymentID"),
        serialization_alias="PaymentId",
    )
    user_telegram_id: Optional[int] = Field(default=None, alias="UserTelegramId")
    wallet: Optional[str] = Field(default=None, alias="Wallet")
    hash: Optional[str] = Field(default=None, alias="Hash")
    tron_amount: Optional[TronDecimal] = Field(default=None, alias="TronAmount")
    actual_tron_amount: Optional[TronDecimal] = Field(default=None, alias="ActualTronAmount")
    user_paid_toman_amount: Optional[int] = Field(default=None, alias="UserPaidTomanAmount")
    toman_amount_without_wage: Optional[int] = Field(default=None, alias="TomanAmountWithoutWage")
    order_status_id: Optional[int] = Field(default=None, alias="OrderStatusID")
    order_status_title: Optional[str] = Field(default=None, alias="OrderStatusTitle")
    is_paid: bool = Field(default=False, alias="IsPaid")
    payment_date: Optional[FlexibleDateTime] = Field(default=None, alias="PaymentDate")

    @property
    def is_payment_accepted(self) -> bool:
        """``True`` when this callback represents a successful payment."""
        return self.is_paid or self.order_status_id == OrderStatusCode.PAYMENT_ACCEPTED

    @property
    def dedup_key(self) -> Tuple[Optional[str], Optional[int]]:
        """``(payment_id, order_status_id)`` — the documented idempotency key."""
        return (self.payment_id, self.order_status_id)


__all__ = ["CallbackPayload"]
