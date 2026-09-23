"""Models for the inbound callbacks (Tronado → your server): the IPN and the dispute."""

from __future__ import annotations

from decimal import Decimal
from typing import Optional, Tuple

from pydantic import AliasChoices, Field

from ..constants import DisputeEvent, DisputeOutcome, DisputeTypeCode, OrderStatusCode
from .base import FlexibleDateTime, TronadoModel, TronDecimal, to_known_enum


class CallbackPayload(TronadoModel):
    """Body that Tronado POSTs to your ``CallbackUrl`` on every order status change.

    One callback is sent per status change (not only on success). De-duplicate using
    :attr:`dedup_key`.

    Which Toman amount to credit the user with depends on the
    ``wage_from_business_percentage`` you passed to ``get_order_token``:

    * ``0`` (default, the user pays the fee): credit :attr:`toman_amount_without_wage`.
      Crediting :attr:`user_paid_toman_amount` here would hand Tronado's fee to the user
      out of your own pocket.
    * ``100`` (you absorb the fee): credit :attr:`user_paid_toman_amount`, which is
      roughly your invoice's base value.
    * Anything in between: credit your own invoice value, i.e. the TRX amount you sent to
      ``GetOrderToken`` times the TRX price (:attr:`tron_price_toman`).

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
        tron_amount: TRX delivered to you: the whole invoice with a wage percentage of
            ``0``, net of the fee with ``100``.
        actual_tron_amount: Original TRX amount before any adjustment.
        user_paid_toman_amount: (v5) Toman the user actually paid, fee included.
        toman_amount_without_wage: (v5) Toman value of the TRX delivered to you, fee
            excluded. Credit this in the default (``0``) wage mode.
        order_status_id: Numeric status (``30`` == ``PaymentAccepted``).
        order_status_title: Persian, display-only status title.
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
    def order_status(self) -> Optional[OrderStatusCode]:
        """The documented :class:`OrderStatusCode` for this callback, or ``None``.

        Returns ``None`` for a missing or not-yet-documented id, so new server-side
        statuses never raise. Use :attr:`order_status_id` for the raw value.
        """
        return to_known_enum(OrderStatusCode, self.order_status_id)

    @property
    def is_payment_accepted(self) -> bool:
        """``True`` only for a successful, final payment (``IsPaid`` or status ``30``)."""
        return self.is_paid or self.order_status_id == OrderStatusCode.PAYMENT_ACCEPTED

    @property
    def dedup_key(self) -> Tuple[Optional[str], Optional[int]]:
        """``(payment_id, order_status_id)`` — the documented idempotency key."""
        return (self.payment_id, self.order_status_id)

    @property
    def tron_price_toman(self) -> Optional[Decimal]:
        """Toman price of one TRX in this order: ``TomanAmountWithoutWage ÷ TronAmount``.

        ``None`` if either amount is missing or ``TronAmount`` is zero.
        """
        if self.toman_amount_without_wage is None or not self.tron_amount:
            return None
        return Decimal(self.toman_amount_without_wage) / self.tron_amount


class DisputeCallbackPayload(TronadoModel):
    """Body Tronado POSTs to your ``DisputeCallbackUrl`` when it accepts a dispute.

    After an order is approved, the card holder may dispute it (e.g. "no deposit was
    made" or "less was deposited"). If Tronado accepts the dispute, the order is either
    annulled or its amount is corrected, and this webhook tells you so. It is opt-in:
    register a public https URL in the Tronado mini app (Business → Settings) or via
    support. It goes to that URL, never to the order's ``CallbackUrl``, and is signed
    exactly like the IPN (``X-Tronado-Sig`` with the same ``IpnSigningKey``). Rejected or
    pending disputes produce no callback.

    Delivery is at least once, so de-duplicate on :attr:`dedup_key` (``DisputeId``).
    Branch on :attr:`outcome`, not on the dispute type:

    * ``Annulled`` (:attr:`is_annulled`): the money never reached the card holder, or the
      receipt was a duplicate, and the order is cancelled. Reverse whatever you granted
      for :attr:`payment_id`, like a chargeback. You also receive the regular IPN with
      ``OrderStatusID == 200``; the two may arrive in either order.
    * ``AmountAdjusted`` (:attr:`is_amount_adjusted`): the user deposited a different
      amount and the order was corrected to it. Adjust the user's balance by
      :attr:`user_must_pay_toman_delta` / :attr:`tron_amount_delta`.
    * Anything else (``NoChange`` is reserved and not sent today): log it, take no action.

    Attributes:
        event: Event type; always ``DisputeAccepted`` today (see :attr:`is_dispute_accepted`).
        event_id: GUID of this event; unchanged across delivery retries.
        dispute_id: Dispute id — the de-duplication key.
        dispute_type: ``NoDeposit`` / ``ReceiptIsRepetitive`` / ``AmountIsLess`` /
            ``AmountIsInRial`` / ``AmountIsMore``.
        dispute_type_id: Numeric dispute type (see :class:`DisputeTypeCode`).
        dispute_type_title: Persian, display-only dispute type title.
        outcome: Effect on the order: ``Annulled`` or ``AmountAdjusted``.
        unique_code: The order's ``UniqueCode`` (as in the IPN).
        payment_id: Your application's payment id.
        raised_at: When the dispute was raised (UTC).
        resolved_at: When the dispute was accepted (UTC).
        original_tron_amount: Order TRX amount before the dispute.
        original_user_must_pay_toman: Order Toman amount before the dispute.
        tron_amount: Order TRX amount after the dispute (``0`` when annulled).
        user_must_pay_toman: Order Toman amount after the dispute (``0`` when annulled).
        tron_amount_delta: ``tron_amount - original_tron_amount`` (negative = less).
        user_must_pay_toman_delta: ``user_must_pay_toman - original_user_must_pay_toman``.
        order_status_id: Current order status (``30`` or ``200``).
        order_status_title: Persian, display-only status title.
        is_paid: Whether the order still counts as paid (``False`` when annulled).
    """

    event: str = Field(alias="Event")
    event_id: Optional[str] = Field(default=None, alias="EventId")
    dispute_id: int = Field(alias="DisputeId")
    dispute_type: Optional[str] = Field(default=None, alias="DisputeType")
    dispute_type_id: Optional[int] = Field(default=None, alias="DisputeTypeID")
    dispute_type_title: Optional[str] = Field(default=None, alias="DisputeTypeTitle")
    outcome: Optional[str] = Field(default=None, alias="Outcome")
    unique_code: Optional[str] = Field(default=None, alias="UniqueCode")
    payment_id: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("PaymentId", "PaymentID"),
        serialization_alias="PaymentId",
    )
    raised_at: Optional[FlexibleDateTime] = Field(default=None, alias="RaisedAt")
    resolved_at: Optional[FlexibleDateTime] = Field(default=None, alias="ResolvedAt")
    original_tron_amount: Optional[TronDecimal] = Field(default=None, alias="OriginalTronAmount")
    original_user_must_pay_toman: Optional[int] = Field(
        default=None, alias="OriginalUserMustPayToman"
    )
    tron_amount: Optional[TronDecimal] = Field(default=None, alias="TronAmount")
    user_must_pay_toman: Optional[int] = Field(default=None, alias="UserMustPayToman")
    tron_amount_delta: Optional[TronDecimal] = Field(default=None, alias="TronAmountDelta")
    user_must_pay_toman_delta: Optional[int] = Field(default=None, alias="UserMustPayTomanDelta")
    order_status_id: Optional[int] = Field(default=None, alias="OrderStatusID")
    order_status_title: Optional[str] = Field(default=None, alias="OrderStatusTitle")
    is_paid: bool = Field(default=False, alias="IsPaid")

    @property
    def is_dispute_accepted(self) -> bool:
        """``True`` for the (only documented) ``DisputeAccepted`` event."""
        return self.event == DisputeEvent.DISPUTE_ACCEPTED

    @property
    def outcome_code(self) -> Optional[DisputeOutcome]:
        """The documented :class:`DisputeOutcome`, or ``None`` if missing or unknown."""
        return to_known_enum(DisputeOutcome, self.outcome)

    @property
    def is_annulled(self) -> bool:
        """``True`` if the order was cancelled by the dispute."""
        return self.outcome == DisputeOutcome.ANNULLED

    @property
    def is_amount_adjusted(self) -> bool:
        """``True`` if the order amount was corrected by the dispute."""
        return self.outcome == DisputeOutcome.AMOUNT_ADJUSTED

    @property
    def dispute_type_code(self) -> Optional[DisputeTypeCode]:
        """The documented :class:`DisputeTypeCode`, or ``None`` if missing or unknown."""
        return to_known_enum(DisputeTypeCode, self.dispute_type_id)

    @property
    def order_status(self) -> Optional[OrderStatusCode]:
        """The documented :class:`OrderStatusCode` of the order now, or ``None``."""
        return to_known_enum(OrderStatusCode, self.order_status_id)

    @property
    def dedup_key(self) -> int:
        """``DisputeId`` — the documented de-duplication key."""
        return self.dispute_id


__all__ = ["CallbackPayload", "DisputeCallbackPayload"]
