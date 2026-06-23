"""Synchronous quickstart.

Run with your API key in the environment:

    export TRONADO_API_KEY="YOUR_API_KEY"
    python examples/quickstart.py
"""

from __future__ import annotations

from decimal import Decimal

from tronado import TronadoClient
from tronado.exceptions import OrderNotFoundError, TronadoError


def main() -> None:
    # api_key is read from the TRONADO_API_KEY environment variable.
    with TronadoClient() as tron:
        # 1. Get Tronado's TRX price (it differs from public exchanges).
        price = tron.price.tron.get_price_to_toman()
        print(f"1 TRX = {price.tron_price_toman:,} Toman (${price.tron_price_dollar})")

        # 2. Create an order and obtain a payment link.
        order = tron.order.get_order_token(
            payment_id="inv-1001",
            wallet_address="TXYZ12345abcdef...",
            tron_amount=Decimal("12.123456"),
            callback_url="https://your-domain.com/payment/callback",
            wage_from_business_percentage=0,
        )
        print("Open this link to pay:", order.full_payment_url)
        if order.estimated_toman_amount:
            print("Estimated Toman amount:", order.estimated_toman_amount)

        # 3. Check the order status later.
        try:
            status = tron.order.get_status_by_payment_id(id="inv-1001")
            print("Paid?", status.is_payment_accepted, "| status:", status.order_status_title)
        except OrderNotFoundError:
            print("No order found for that payment id yet.")


if __name__ == "__main__":
    try:
        main()
    except TronadoError as exc:
        raise SystemExit(f"Tronado error: {exc}") from exc
