"""Verify and handle Tronado IPN and dispute callbacks with FastAPI.

Tronado POSTs to your ``CallbackUrl`` on every order status change, signing the request
with ``X-Tronado-Sig = HMAC_SHA512(raw_body, IPN_SIGNING_KEY)`` (lowercase hex). You must
verify against the **raw** request body before parsing. If you enabled dispute callbacks
(mini app → Business → Settings), accepted disputes are POSTed to your separate
``DisputeCallbackUrl``, signed the same way.

    export TRONADO_IPN_SIGNING_KEY="YOUR_IPN_SIGNING_KEY"
    uvicorn examples.fastapi_webhook:app --reload

Expose it publicly (e.g. with ngrok), register the domain with Tronado support, and pass
that URL as ``callback_url`` when creating orders. For local testing, send the Tronado
bot ``/dummyrequest <your_callback_url>``.
"""

from __future__ import annotations

import os

from fastapi import FastAPI, Request, Response

from tronado.exceptions import InvalidSignatureError, TronadoWebhookError
from tronado.webhook import construct_dispute_event, construct_event

app = FastAPI()

IPN_SIGNING_KEY = os.environ["TRONADO_IPN_SIGNING_KEY"]

# In production use a shared/persistent store (Redis, DB) for idempotency.
_processed: set[tuple] = set()
_processed_disputes: set[int] = set()


@app.post("/payment/callback")
async def payment_callback(request: Request) -> Response:
    raw_body = await request.body()  # the exact bytes — do not re-serialize
    signature = request.headers.get("X-Tronado-Sig", "")

    try:
        event = construct_event(raw_body, signature, IPN_SIGNING_KEY)
    except InvalidSignatureError:
        # Reject forged/unsigned requests.
        return Response(status_code=401)
    except TronadoWebhookError:
        # Signature was valid but the body was malformed.
        return Response(status_code=400)

    # De-duplicate: the same (payment_id, status) may be delivered more than once.
    if event.dedup_key in _processed:
        return Response(status_code=200)
    _processed.add(event.dedup_key)

    if event.is_payment_accepted:
        # Orders here use the default wage mode (0, the user pays the fee), so credit
        # the Toman value of the TRX received. With wage 100 you would credit
        # event.user_paid_toman_amount instead (see CallbackPayload).
        print(
            f"Payment accepted: payment_id={event.payment_id} "
            f"credit_toman={event.toman_amount_without_wage} txid={event.hash}"
        )
        # credit_user(event.payment_id, event.toman_amount_without_wage)
    else:
        print(f"Status update for {event.payment_id}: {event.order_status_title}")

    # Acknowledge with 2xx; otherwise Tronado will retry.
    return Response(status_code=200)


@app.post("/payment/dispute")
async def dispute_callback(request: Request) -> Response:
    raw_body = await request.body()
    signature = request.headers.get("X-Tronado-Sig", "")

    try:
        event = construct_dispute_event(raw_body, signature, IPN_SIGNING_KEY)
    except InvalidSignatureError:
        return Response(status_code=401)
    except TronadoWebhookError:
        return Response(status_code=400)

    # Delivery is at least once: de-duplicate on DisputeId. Unknown future event types
    # are acknowledged and ignored.
    if not event.is_dispute_accepted or event.dedup_key in _processed_disputes:
        return Response(status_code=200)
    _processed_disputes.add(event.dedup_key)

    if event.is_annulled:
        # The order was cancelled: reverse what was granted (like a chargeback).
        print(f"Dispute {event.dispute_id}: annul payment_id={event.payment_id}")
        # reverse_credit(event.payment_id)
    elif event.is_amount_adjusted:
        print(
            f"Dispute {event.dispute_id}: adjust payment_id={event.payment_id} "
            f"by {event.user_must_pay_toman_delta} Toman ({event.tron_amount_delta} TRX)"
        )
        # adjust_credit(event.payment_id, event.user_must_pay_toman_delta)
    else:
        # Reserved/unknown outcome (e.g. NoChange): log only.
        print(f"Dispute {event.dispute_id}: outcome {event.outcome!r}, no action")

    # 2xx acknowledges. If your own processing fails temporarily, return 5xx instead:
    # Tronado retries 5xx/408/429/timeouts, but never a permanent 4xx.
    return Response(status_code=200)
