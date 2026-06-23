"""Tests for the Pydantic models (aliasing, coercion, helpers)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from tronado.constants import OrderStatusCode
from tronado.models import (
    CallbackPayload,
    GetOrderTokenRequest,
    OrderStatus,
)

# (OrderStatusID, enum member name) for every status documented in the Postman docs.
DOCUMENTED_STATUSES = [
    (20, "WAITING_FOR_PAYMENT"),
    (25, "PHOTO_SENT_TO_ADMIN"),
    (27, "READY_TO_TRANSFER"),
    (30, "PAYMENT_ACCEPTED"),
    (40, "PAYMENT_REJECTED"),
    (200, "CANCELLED"),
]


def test_request_serializes_to_pascal_case() -> None:
    req = GetOrderTokenRequest(
        payment_id="p1",
        wallet_address="T123",
        tron_amount="12.123456",
        callback_url="https://x.com/cb",
    )
    dumped = req.model_dump(by_alias=True)
    assert dumped == {
        "PaymentID": "p1",
        "WalletAddress": "T123",
        "TronAmount": Decimal("12.123456"),
        "CallbackUrl": "https://x.com/cb",
    }


def test_callback_url_must_be_https() -> None:
    with pytest.raises(ValidationError):
        GetOrderTokenRequest(
            payment_id="p",
            wallet_address="T",
            tron_amount="1",
            callback_url="http://insecure.com/cb",
        )


def test_decimal_coercion_avoids_float_noise() -> None:
    req = GetOrderTokenRequest(
        payment_id="p", wallet_address="T", tron_amount=0.1, callback_url="https://x/cb"
    )
    assert req.tron_amount == Decimal("0.1")


def test_status_response_parses_pascal_case() -> None:
    status = OrderStatus.model_validate(
        {
            "UniqueCode": "u",
            "PaymentID": "p1",
            "UserTelegramId": 123456789,
            "TronAmount": 100.25,
            "OrderStatusID": 30,
            "IsPaid": True,
            "PaymentDate": "2025-09-09T15:30:00Z",
        }
    )
    assert status.payment_id == "p1"
    assert status.user_telegram_id == 123456789
    assert status.tron_amount == Decimal("100.25")
    assert status.is_payment_accepted is True
    assert isinstance(status.payment_date, datetime)


def test_status_is_payment_accepted_via_status_id_without_is_paid() -> None:
    status = OrderStatus.model_validate({"OrderStatusID": 30, "IsPaid": False})
    assert status.is_payment_accepted is True
    other = OrderStatus.model_validate({"OrderStatusID": 10, "IsPaid": False})
    assert other.is_payment_accepted is False


def test_order_status_code_enum_matches_documentation() -> None:
    # Exactly the six documented ids/values — no more, no less.
    assert {member.value for member in OrderStatusCode} == {20, 25, 27, 30, 40, 200}
    assert OrderStatusCode.PAYMENT_ACCEPTED == 30


@pytest.mark.parametrize("status_id,member", DOCUMENTED_STATUSES)
def test_order_status_parses_every_documented_id(status_id: int, member: str) -> None:
    # IsPaid defaults to False, so acceptance is driven purely by the status id.
    status = OrderStatus.model_validate({"OrderStatusID": status_id})
    assert status.order_status_id == status_id
    assert status.order_status is OrderStatusCode[member]
    assert status.is_payment_accepted is (status_id == 30)


def test_order_status_unknown_id_is_forward_compatible() -> None:
    status = OrderStatus.model_validate({"OrderStatusID": 9999})
    assert status.order_status_id == 9999
    assert status.order_status is None  # unknown id does not raise
    assert status.is_payment_accepted is False


def test_order_status_is_paid_true_accepts_regardless_of_id() -> None:
    # The docs allow detecting success via IsPaid == true as well.
    status = OrderStatus.model_validate({"OrderStatusID": 27, "IsPaid": True})
    assert status.is_payment_accepted is True


def test_callback_payment_id_lowercase_d_alias_and_overlong_fraction() -> None:
    # The webhook uses 'PaymentId' (lowercase d) and 7-digit fractional seconds.
    cb = CallbackPayload.model_validate(
        {
            "PaymentId": "p1",
            "UserPaidTomanAmount": 102030,
            "TomanAmountWithoutWage": 84085,
            "OrderStatusID": 30,
            "IsPaid": True,
            "PaymentDate": "2026-06-20T15:27:00.1830000",
        }
    )
    assert cb.payment_id == "p1"
    assert cb.user_paid_toman_amount == 102030
    assert cb.dedup_key == ("p1", 30)
    assert cb.is_payment_accepted is True
    assert cb.payment_date == datetime(2026, 6, 20, 15, 27, 0, 183000)


def test_unknown_fields_are_ignored_for_forward_compat() -> None:
    status = OrderStatus.model_validate({"PaymentID": "p", "SomeFutureField": 123})
    assert status.payment_id == "p"
    assert not hasattr(status, "some_future_field")
