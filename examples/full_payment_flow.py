"""End-to-end payment flow: price -> compute TRX -> create order -> poll status.

This shows how the pieces fit together. In production you would rely on the **webhook**
(see ``fastapi_webhook.py``) to learn about payment instead of polling, but polling is
handy for scripts and testing.

    export TRONADO_API_KEY="YOUR_API_KEY"
    python examples/full_payment_flow.py
"""

from __future__ import annotations

import time
from decimal import Decimal

from tronado import TronadoClient
from tronado.constants import OrderStatusCode
from tronado.exceptions import OrderNotFoundError

DESTINATION_WALLET = "TXYZ12345abcdef..."
PAYMENT_ID = "order-9001"
INVOICE_TOMAN = 500_000  # what you want to collect, in Toman


def main() -> None:
    with TronadoClient() as tron:
        # 1. Convert your Toman invoice into the TRX amount to request.
        conversion = tron.price.toman.convert_to_tron_wage_subtracted(
            toman=INVOICE_TOMAN, wallet=DESTINATION_WALLET
        )
        tron_amount: Decimal = conversion.tron_amount
        print(f"{INVOICE_TOMAN:,} Toman -> request {tron_amount} TRX")

        # 2. Create the order.
        order = tron.order.get_order_token(
            payment_id=PAYMENT_ID,
            wallet_address=DESTINATION_WALLET,
            tron_amount=tron_amount,
            callback_url="https://your-domain.com/payment/callback",
        )
        print("Ask the customer to pay at:", order.full_payment_url)

        # 3. Poll for completion (max ~2 minutes). Prefer webhooks in production.
        for attempt in range(24):
            try:
                status = tron.order.get_status_by_payment_id(id=PAYMENT_ID)
            except OrderNotFoundError:
                status = None

            if status and status.is_payment_accepted:
                print(f"Payment accepted (status {OrderStatusCode.PAYMENT_ACCEPTED}).")
                print("TXID:", status.hash)
                return

            print(f"  [{attempt + 1}/24] not paid yet; waiting...")
            time.sleep(5)

        print("Timed out waiting for payment.")


if __name__ == "__main__":
    main()
