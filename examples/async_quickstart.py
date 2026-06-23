"""Asynchronous quickstart.

    export TRONADO_API_KEY="YOUR_API_KEY"
    python examples/async_quickstart.py
"""

from __future__ import annotations

import asyncio

from tronado import AsyncTronadoClient
from tronado.exceptions import TronadoError


async def main() -> None:
    async with AsyncTronadoClient() as tron:
        # Fetch several independent prices concurrently.
        tron_price, dollar_price = await asyncio.gather(
            tron.price.tron.get_price_to_toman(),
            tron.price.dollar.get_price_to_toman(),
        )
        print(f"1 TRX = {tron_price.tron_price_toman:,} Toman")
        print(f"1 USD = {dollar_price.dollar_price:,} Toman")

        order = await tron.order.get_order_token(
            payment_id="inv-2002",
            wallet_address="TXYZ12345abcdef...",
            tron_amount="8.5",
            callback_url="https://your-domain.com/payment/callback",
        )
        print("Pay here:", order.full_payment_url)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except TronadoError as exc:
        raise SystemExit(f"Tronado error: {exc}") from exc
