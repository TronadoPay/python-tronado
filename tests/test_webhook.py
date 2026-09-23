"""Tests for the inbound IPN/webhook helpers."""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from tronado.constants import DisputeOutcome, DisputeTypeCode, OrderStatusCode
from tronado.exceptions import InvalidSignatureError, TronadoWebhookError
from tronado.webhook import (
    compute_signature,
    construct_dispute_event,
    construct_event,
    parse_callback,
    parse_dispute_callback,
    verify_signature,
)

SIGNING_KEY = "ipn-secret-key"
RAW = json.dumps(
    {
        "UniqueCode": "3f2a9c",
        "PaymentId": "YOUR_PAYMENT_ID",
        "UserTelegramId": 123456789,
        "UserPaidTomanAmount": 102030,
        "TomanAmountWithoutWage": 84085,
        "OrderStatusID": 30,
        "IsPaid": True,
        "PaymentDate": "2026-06-20T15:27:00.1830000",
    }
).encode("utf-8")


def _sign(body: bytes, key: str = SIGNING_KEY) -> str:
    return hmac.new(key.encode(), body, hashlib.sha512).hexdigest()


def test_compute_signature_matches_reference_hmac() -> None:
    assert compute_signature(RAW, SIGNING_KEY) == _sign(RAW)


def test_verify_signature_roundtrip() -> None:
    sig = compute_signature(RAW, SIGNING_KEY)
    assert verify_signature(RAW, sig, SIGNING_KEY) is True
    # Header comparison is case-insensitive (hex).
    assert verify_signature(RAW, sig.upper(), SIGNING_KEY) is True


def test_verify_rejects_tampered_body() -> None:
    sig = compute_signature(RAW, SIGNING_KEY)
    tampered = RAW.replace(b"102030", b"999999")
    assert verify_signature(tampered, sig, SIGNING_KEY) is False


def test_verify_rejects_wrong_key_and_missing_header() -> None:
    sig = compute_signature(RAW, SIGNING_KEY)
    assert verify_signature(RAW, sig, "wrong-key") is False
    assert verify_signature(RAW, None, SIGNING_KEY) is False


def test_parse_callback_returns_typed_payload() -> None:
    payload = parse_callback(RAW)
    assert payload.payment_id == "YOUR_PAYMENT_ID"
    assert payload.user_paid_toman_amount == 102030
    assert payload.is_payment_accepted is True


def test_callback_accepts_both_payment_id_spellings() -> None:
    # v5 uses PaymentId; accept the PaymentID spelling too for robustness.
    lower_d = parse_callback(b'{"PaymentId": "abc", "OrderStatusID": 30}')
    upper_d = parse_callback(b'{"PaymentID": "abc", "OrderStatusID": 30}')
    assert lower_d.payment_id == upper_d.payment_id == "abc"
    # Serializes back to the documented PaymentId spelling.
    assert upper_d.model_dump(by_alias=True)["PaymentId"] == "abc"


def test_parse_callback_rejects_invalid_json() -> None:
    with pytest.raises(TronadoWebhookError):
        parse_callback(b"{not json")


@pytest.mark.parametrize("status_id", [20, 25, 27, 30, 40, 200])
def test_callback_parses_every_documented_status(status_id: int) -> None:
    body = json.dumps({"PaymentId": "p", "OrderStatusID": status_id}).encode()
    cb = parse_callback(body)
    assert cb.order_status_id == status_id
    assert cb.order_status is OrderStatusCode(status_id)
    # IsPaid defaults False here, so only status 30 is accepted.
    assert cb.is_payment_accepted is (status_id == 30)


def test_callback_unknown_status_is_forward_compatible() -> None:
    cb = parse_callback(b'{"PaymentId": "p", "OrderStatusID": 9999}')
    assert cb.order_status_id == 9999
    assert cb.order_status is None
    assert cb.is_payment_accepted is False


def test_construct_event_verifies_then_parses() -> None:
    sig = compute_signature(RAW, SIGNING_KEY)
    event = construct_event(RAW, sig, SIGNING_KEY)
    assert event.dedup_key == ("YOUR_PAYMENT_ID", 30)


def test_construct_event_raises_on_bad_signature() -> None:
    with pytest.raises(InvalidSignatureError):
        construct_event(RAW, "deadbeef", SIGNING_KEY)


def test_str_body_is_accepted() -> None:
    body = RAW.decode("utf-8")
    sig = compute_signature(body, SIGNING_KEY)
    assert verify_signature(body, sig, SIGNING_KEY) is True


# --------------------------------------------------------------------------- disputes

# The three dispute callback samples from the docs, verbatim.
DISPUTE_AMOUNT_IS_LESS = {
    "Event": "DisputeAccepted",
    "EventId": "c2a9e7d0-1b3f-4a6c-8e5d-7f0a1b2c3d4e",
    "DisputeId": 48302,
    "DisputeType": "AmountIsLess",
    "DisputeTypeID": 41,
    "DisputeTypeTitle": "مبلغ کمتر واریز شده",
    "Outcome": "AmountAdjusted",
    "UniqueCode": "a1b2c3d4e5f60718293a4b5c6d7e8f90",
    "PaymentId": "INV-20260922-1203",
    "RaisedAt": "2026-09-22T11:03:20Z",
    "ResolvedAt": "2026-09-22T11:40:02Z",
    "OriginalTronAmount": 30.0,
    "OriginalUserMustPayToman": 1500000,
    "TronAmount": 24.0,
    "UserMustPayToman": 1200000,
    "TronAmountDelta": -6.0,
    "UserMustPayTomanDelta": -300000,
    "OrderStatusID": 30,
    "OrderStatusTitle": "تایید شده",
    "IsPaid": True,
}
DISPUTE_NO_DEPOSIT = {
    "Event": "DisputeAccepted",
    "EventId": "8f3c1e2a-5b7d-4c0e-9a11-2d4f6b8c0e13",
    "DisputeId": 48213,
    "DisputeType": "NoDeposit",
    "DisputeTypeID": 1,
    "DisputeTypeTitle": "واریزی انجام نشده",
    "Outcome": "Annulled",
    "UniqueCode": "3f9d2c1a7b4e4e0f9c8d1a2b3c4d5e6f",
    "PaymentId": "INV-20260922-1187",
    "RaisedAt": "2026-09-22T09:41:07Z",
    "ResolvedAt": "2026-09-22T10:12:55Z",
    "OriginalTronAmount": 30.0,
    "OriginalUserMustPayToman": 1500000,
    "TronAmount": 0,
    "UserMustPayToman": 0,
    "TronAmountDelta": -30.0,
    "UserMustPayTomanDelta": -1500000,
    "OrderStatusID": 200,
    "OrderStatusTitle": "لغو شده",
    "IsPaid": False,
}
DISPUTE_AMOUNT_IS_MORE = {
    "Event": "DisputeAccepted",
    "EventId": "5d6e7f80-9a1b-4c2d-8e3f-0a1b2c3d4e5f",
    "DisputeId": 48377,
    "DisputeType": "AmountIsMore",
    "DisputeTypeID": 31,
    "DisputeTypeTitle": "مبلغ بیشتر واریز شده",
    "Outcome": "AmountAdjusted",
    "UniqueCode": "0f1e2d3c4b5a69788796a5b4c3d2e1f0",
    "PaymentId": "INV-20260922-1219",
    "RaisedAt": "2026-09-22T12:15:44Z",
    "ResolvedAt": "2026-09-22T12:58:31Z",
    "OriginalTronAmount": 30.0,
    "OriginalUserMustPayToman": 1500000,
    "TronAmount": 36.0,
    "UserMustPayToman": 1800000,
    "TronAmountDelta": 6.0,
    "UserMustPayTomanDelta": 300000,
    "OrderStatusID": 30,
    "OrderStatusTitle": "تایید شده",
    "IsPaid": True,
}


def _raw(payload: dict) -> bytes:
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def test_construct_dispute_event_amount_adjusted() -> None:
    raw = _raw(DISPUTE_AMOUNT_IS_LESS)
    # Signed exactly like the IPN: same header, same key.
    event = construct_dispute_event(raw, compute_signature(raw, SIGNING_KEY), SIGNING_KEY)

    assert event.is_dispute_accepted is True
    assert event.event_id == "c2a9e7d0-1b3f-4a6c-8e5d-7f0a1b2c3d4e"
    assert event.dedup_key == 48302
    assert event.dispute_type == "AmountIsLess"
    assert event.dispute_type_code is DisputeTypeCode.AMOUNT_IS_LESS
    assert event.outcome_code is DisputeOutcome.AMOUNT_ADJUSTED
    assert event.is_amount_adjusted is True
    assert event.is_annulled is False
    assert event.payment_id == "INV-20260922-1203"
    assert event.raised_at == datetime(2026, 9, 22, 11, 3, 20, tzinfo=timezone.utc)
    assert event.resolved_at == datetime(2026, 9, 22, 11, 40, 2, tzinfo=timezone.utc)
    assert event.original_tron_amount == Decimal("30.0")
    assert event.tron_amount == Decimal("24.0")
    assert event.tron_amount_delta == Decimal("-6.0")
    assert event.original_user_must_pay_toman == 1500000
    assert event.user_must_pay_toman == 1200000
    assert event.user_must_pay_toman_delta == -300000
    assert event.order_status is OrderStatusCode.PAYMENT_ACCEPTED
    assert event.is_paid is True


def test_parse_dispute_callback_annulled() -> None:
    event = parse_dispute_callback(_raw(DISPUTE_NO_DEPOSIT))
    assert event.dispute_type_code is DisputeTypeCode.NO_DEPOSIT
    assert event.outcome_code is DisputeOutcome.ANNULLED
    assert event.is_annulled is True
    assert event.is_amount_adjusted is False
    assert event.tron_amount == 0
    assert event.user_must_pay_toman == 0
    assert event.tron_amount_delta == Decimal("-30.0")
    # An annulled order is cancelled and no longer counts as paid.
    assert event.order_status is OrderStatusCode.CANCELLED
    assert event.is_paid is False


def test_parse_dispute_callback_amount_is_more() -> None:
    event = parse_dispute_callback(_raw(DISPUTE_AMOUNT_IS_MORE))
    assert event.dispute_type_code is DisputeTypeCode.AMOUNT_IS_MORE
    assert event.is_amount_adjusted is True
    assert event.tron_amount_delta == Decimal("6.0")
    assert event.user_must_pay_toman_delta == 300000


@pytest.mark.parametrize("outcome", ["NoChange", "SomeFutureOutcome"])
def test_dispute_unknown_or_reserved_outcome_needs_no_action(outcome: str) -> None:
    event = parse_dispute_callback(_raw({**DISPUTE_AMOUNT_IS_LESS, "Outcome": outcome}))
    assert event.outcome == outcome
    assert event.is_annulled is False
    assert event.is_amount_adjusted is False
    expected = DisputeOutcome.NO_CHANGE if outcome == "NoChange" else None
    assert event.outcome_code is expected


def test_dispute_unknown_event_and_type_are_forward_compatible() -> None:
    event = parse_dispute_callback(
        _raw({**DISPUTE_AMOUNT_IS_LESS, "Event": "DisputeRaised", "DisputeTypeID": 999})
    )
    assert event.is_dispute_accepted is False
    assert event.dispute_type_code is None


def test_construct_dispute_event_raises_on_bad_signature() -> None:
    with pytest.raises(InvalidSignatureError):
        construct_dispute_event(_raw(DISPUTE_NO_DEPOSIT), "deadbeef", SIGNING_KEY)


@pytest.mark.parametrize("missing", ["Event", "DisputeId"])
def test_dispute_without_event_or_dispute_id_is_rejected(missing: str) -> None:
    # DisputeId is the de-duplication key and Event the discriminator: both required.
    payload = {k: v for k, v in DISPUTE_NO_DEPOSIT.items() if k != missing}
    with pytest.raises(TronadoWebhookError, match="Dispute callback"):
        parse_dispute_callback(_raw(payload))


def test_parse_dispute_callback_rejects_invalid_json() -> None:
    with pytest.raises(TronadoWebhookError):
        parse_dispute_callback(b"{not json")
