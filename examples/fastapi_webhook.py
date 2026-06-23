"""Verify and handle Tronado IPN/webhook callbacks with FastAPI.

Tronado POSTs to your ``CallbackUrl`` on every order status change, signing the request
with ``X-Tronado-Sig = HMAC_SHA512(raw_body, IPN_SIGNING_KEY)`` (lowercase hex). You must
verify against the **raw** request body before parsing.

    export TRONADO_IPN_SIGNING_KEY="YOUR_IPN_SIGNING_KEY"
    uvicorn examples.fastapi_webhook:app --reload

Expose it publicly (e.g. with ngrok) and pass that URL as ``callback_url`` when creating
orders. For local testing, send the Tronado bot ``/dummyrequest <your_callback_url>``.
"""

from __future__ import annotations

import os

from fastapi import FastAPI, Request, Response

from tronado.exceptions import InvalidSignatureError, TronadoWebhookError
from tronado.webhook import construct_event

app = FastAPI()

IPN_SIGNING_KEY = os.environ["TRONADO_IPN_SIGNING_KEY"]

# In production use a shared/persistent store (Redis, DB) for idempotency.
_processed: set[tuple] = set()


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
        # Charge the user with what they actually paid (includes wage).
        print(
            f"Payment accepted: payment_id={event.payment_id} "
            f"user_paid_toman={event.user_paid_toman_amount} txid={event.hash}"
        )
        # credit_user(event.payment_id, event.user_paid_toman_amount)
    else:
        print(f"Status update for {event.payment_id}: {event.order_status_title}")

    # Acknowledge with 2xx; otherwise Tronado will retry.
    return Response(status_code=200)
