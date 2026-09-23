"""Request and response models for the ``Order`` resource."""

from __future__ import annotations

from typing import Optional
from urllib.parse import quote

from pydantic import Field, field_validator

from ..constants import PAYMENT_PAGE_URL_TEMPLATE, OrderStatusCode
from .base import FlexibleDateTime, TronadoModel, TronDecimal, to_known_enum


class GetOrderTokenRequest(TronadoModel):
    """Body for ``POST /api/v5/GetOrderToken``.

    Attributes:
        payment_id: Your application's unique payment identifier.
        wallet_address: Destination TRON wallet address.
        tron_amount: Invoice amount in TRX. Use the price endpoints first to compute it.
        callback_url: HTTPS URL that Tronado will POST payment results to. Its domain
            must be registered with Tronado support, or no callback is sent.
    """

    payment_id: str = Field(alias="PaymentID")
    wallet_address: str = Field(alias="WalletAddress")
    tron_amount: TronDecimal = Field(alias="TronAmount")
    callback_url: str = Field(alias="CallbackUrl")

    @field_validator("callback_url")
    @classmethod
    def _require_https(cls, value: str) -> str:
        if not value.lower().startswith("https://"):
            raise ValueError("callback_url must be an https:// URL")
        return value


class GetStatusRequest(TronadoModel):
    """Body for ``POST /Order/GetStatus`` and ``POST /Order/GetStatusByPaymentID``.

    Attributes:
        id: For ``get_status`` this is the Tronado OrderId, ``TrndOrderID_{id}`` or TXID.
            For ``get_status_by_payment_id`` it is your application's ``PaymentID``.
    """

    id: str = Field(alias="Id")


class OrderTokenData(TronadoModel):
    """``Data`` payload of a successful ``GetOrderToken`` response.

    Attributes:
        token: Transaction token.
        full_payment_url: Ready-to-use payment link.
        error_message: Error detail when the API could not create the order.
        estimated_toman_amount: Estimated Toman amount (string, as returned by the API).
        estimated_toman_amount_expire_date_utc: Expiry of the estimate, in UTC.
    """

    token: str = Field(alias="Token")
    full_payment_url: Optional[str] = Field(default=None, alias="FullPaymentUrl")
    error_message: Optional[str] = Field(default=None, alias="ErrorMessage")
    estimated_toman_amount: Optional[str] = Field(default=None, alias="EstimatedTomanAmount")
    estimated_toman_amount_expire_date_utc: Optional[FlexibleDateTime] = Field(
        default=None, alias="EstimatedTomanAmountExpireDateUtc"
    )

    @property
    def payment_page_url(self) -> str:
        """Deep link to Tronado's payment page (Telegram mini app) for this order.

        Put it behind a button in your own bot: the customer lands straight on the
        payment page without having to start the Tronado bot.
        """
        return PAYMENT_PAGE_URL_TEMPLATE.format(token=quote(self.token, safe=""))


class OrderStatus(TronadoModel):
    """Response of ``GetStatus`` / ``GetStatusByPaymentID`` for an existing order.

    Attributes:
        unique_code: Tronado unique code for the order.
        payment_id: Your application payment id.
        user_telegram_id: Telegram user id of the payer.
        wallet: Destination wallet.
        hash: On-chain transaction hash (TXID).
        tron_amount: Net TRX delivered to you.
        actual_tron_amount: Original TRX amount before any adjustment.
        order_status_id: Numeric status (``30`` == ``PaymentAccepted``).
        order_status_title: Human-readable status title.
        is_paid: Whether the order was paid successfully.
        payment_date: Timestamp of the payment.
    """

    unique_code: Optional[str] = Field(default=None, alias="UniqueCode")
    payment_id: Optional[str] = Field(default=None, alias="PaymentID")
    user_telegram_id: Optional[int] = Field(default=None, alias="UserTelegramId")
    wallet: Optional[str] = Field(default=None, alias="Wallet")
    hash: Optional[str] = Field(default=None, alias="Hash")
    tron_amount: Optional[TronDecimal] = Field(default=None, alias="TronAmount")
    actual_tron_amount: Optional[TronDecimal] = Field(default=None, alias="ActualTronAmount")
    order_status_id: Optional[int] = Field(default=None, alias="OrderStatusID")
    order_status_title: Optional[str] = Field(default=None, alias="OrderStatusTitle")
    is_paid: bool = Field(default=False, alias="IsPaid")
    payment_date: Optional[FlexibleDateTime] = Field(default=None, alias="PaymentDate")

    @property
    def order_status(self) -> Optional[OrderStatusCode]:
        """The documented :class:`OrderStatusCode` for this order, or ``None``.

        Returns ``None`` if no status is present or the id is not (yet) documented, so
        new server-side statuses never raise. Use :attr:`order_status_id` for the raw
        value.
        """
        return to_known_enum(OrderStatusCode, self.order_status_id)

    @property
    def is_payment_accepted(self) -> bool:
        """``True`` only for a successful, final payment (``IsPaid`` or status ``30``)."""
        return self.is_paid or self.order_status_id == OrderStatusCode.PAYMENT_ACCEPTED


__all__ = [
    "GetOrderTokenRequest",
    "GetStatusRequest",
    "OrderTokenData",
    "OrderStatus",
]
