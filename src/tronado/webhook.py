"""Inbound IPN/webhook helpers (Tronado → your server).

Tronado POSTs a JSON callback to your ``CallbackUrl`` on every order status change and
signs it. The documented scheme (with reference Node.js and C# snippets) is:

    X-Tronado-Sig = HMAC_SHA512(raw_json_body, IPN_SIGNING_KEY)   # lowercase hex

computed over the **raw** request bytes *before* any parsing, and compared in constant
time. This module implements exactly that — nothing about the signature is inferred.

Framework-agnostic usage::

    from tronado.webhook import construct_event
    from tronado.exceptions import InvalidSignatureError

    raw = await request.body()                     # the exact bytes received
    sig = request.headers["X-Tronado-Sig"]
    try:
        event = construct_event(raw, sig, signing_key=MY_IPN_KEY)
    except InvalidSignatureError:
        return Response(status_code=401)
    if event.is_payment_accepted:
        credit_user(event.payment_id, event.user_paid_toman_amount)

Always verify the signature on the **raw body**; re-serializing parsed JSON will change
the bytes and break verification.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Union

from .constants import WEBHOOK_SIGNATURE_HEADER
from .exceptions import InvalidSignatureError, TronadoWebhookError
from .models.webhook import CallbackPayload

__all__ = [
    "WEBHOOK_SIGNATURE_HEADER",
    "compute_signature",
    "verify_signature",
    "parse_callback",
    "construct_event",
    "CallbackPayload",
]

RawBody = Union[str, bytes, bytearray]
SigningKey = Union[str, bytes]


def _to_bytes(value: Union[RawBody, SigningKey]) -> bytes:
    if isinstance(value, (bytes, bytearray)):
        return bytes(value)
    if isinstance(value, str):
        return value.encode("utf-8")
    raise TypeError(f"Expected str or bytes, got {type(value).__name__}")


def compute_signature(raw_body: RawBody, signing_key: SigningKey) -> str:
    """Compute the expected ``X-Tronado-Sig`` value for ``raw_body``.

    Args:
        raw_body: The exact request body bytes (or str) as received from Tronado.
        signing_key: Your business IPN signing key (``IpnSigningKey``).

    Returns:
        Lowercase hex HMAC-SHA512 digest.
    """
    return hmac.new(_to_bytes(signing_key), _to_bytes(raw_body), hashlib.sha512).hexdigest()


def verify_signature(
    raw_body: RawBody, signature_header: Union[str, None], signing_key: SigningKey
) -> bool:
    """Constant-time check of a provided signature against the raw body.

    Args:
        raw_body: The exact request body bytes (or str) as received.
        signature_header: The value of the ``X-Tronado-Sig`` header (may be ``None``).
        signing_key: Your business IPN signing key.

    Returns:
        ``True`` if the signature is valid, ``False`` otherwise.
    """
    if not signature_header:
        return False
    expected = compute_signature(raw_body, signing_key)
    provided = signature_header.strip().lower()
    return hmac.compare_digest(expected, provided)


def parse_callback(raw_body: RawBody) -> CallbackPayload:
    """Parse a callback body into a :class:`~tronado.models.webhook.CallbackPayload`.

    This does **not** verify the signature — use :func:`construct_event` (or call
    :func:`verify_signature` first) to do that.

    Raises:
        TronadoWebhookError: If the body is not valid JSON or fails schema validation.
    """
    try:
        data = json.loads(_to_bytes(raw_body))
    except (ValueError, TypeError) as exc:
        raise TronadoWebhookError(f"Callback body is not valid JSON: {exc}") from exc
    try:
        return CallbackPayload.model_validate(data)
    except Exception as exc:  # noqa: BLE001 - normalise to our error type
        raise TronadoWebhookError(f"Callback body failed validation: {exc}") from exc


def construct_event(
    raw_body: RawBody, signature_header: Union[str, None], signing_key: SigningKey
) -> CallbackPayload:
    """Verify the signature and parse the callback in one step.

    Args:
        raw_body: The exact request body bytes as received from Tronado.
        signature_header: Value of the ``X-Tronado-Sig`` header.
        signing_key: Your business IPN signing key.

    Returns:
        The validated callback payload.

    Raises:
        InvalidSignatureError: If signature verification fails.
        TronadoWebhookError: If the (verified) body cannot be parsed.
    """
    if not verify_signature(raw_body, signature_header, signing_key):
        raise InvalidSignatureError(
            "Tronado webhook signature verification failed; rejecting the request."
        )
    return parse_callback(raw_body)
