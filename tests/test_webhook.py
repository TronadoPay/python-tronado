"""Tests for the inbound IPN/webhook helpers."""

from __future__ import annotations

import hashlib
import hmac
import json

import pytest

from tronado.exceptions import InvalidSignatureError, TronadoWebhookError
from tronado.webhook import compute_signature, construct_event, parse_callback, verify_signature

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
