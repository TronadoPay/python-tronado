# Tronado Python SDK

A production-grade, **version-aware** Python SDK for the [Tronado Public API](https://miniapp.tronado.cloud/assets/api-docs.md).
Tronado lets a business accept TRON (TRX) payments: you create an order, the customer
pays through Tronado's payment page (a Telegram mini app), and Tronado notifies your
server with a signed webhook.

- **Sync & async** clients on a single `httpx` core
- **Typed** Pydantic v2 request/response models (amounts are `Decimal`, never `float`)
- **Idempotency-aware retries** — order creation is never silently retried
- **Signed webhooks** — IPN and dispute callbacks, verified with the documented
  `X-Tronado-Sig` HMAC-SHA512 scheme and parsed into typed payloads
- **Designed for API versioning** — v5 today, future versions plug in cleanly

> Currently implements API **v5** (the recommended version).

---

## Installation

```bash
pip install tronado
```

From source (this repository):

```bash
pip install -e ".[dev]"   # includes test/lint tooling
```

Requires Python **3.9+**. Runtime dependencies: `httpx` and `pydantic` (v2).

---

## Authentication

The order endpoints require your API key in the **`x-api-key`** header (this is the
documented scheme — there is no `Authorization: Bearer`). Request a key from
[Tronado support](https://t.me/TronadoSupp).

```python
from tronado import TronadoClient

client = TronadoClient(api_key="YOUR_API_KEY")
```

The price endpoints are public: the SDK never sends your key to them, and you can use
them without one. A keyless client only raises `TronadoConfigError` once you call an
order endpoint (before anything is sent).

```python
with TronadoClient() as tron:   # no key needed for prices
    print(tron.price.tron.get_price_to_toman().tron_price_toman)
```

Or via environment variable (no argument needed):

```bash
export TRONADO_API_KEY="YOUR_API_KEY"
# optional: export TRONADO_BASE_URL="https://bot.tronado.cloud"
```

---

## Configuration

| Option | Default | Description |
|---|---|---|
| `api_key` | `TRONADO_API_KEY` env | API key for the `x-api-key` header (order endpoints only) |
| `base_url` | `https://bot.tronado.cloud` | API base URL (`TRONADO_BASE_URL` honoured) |
| `timeout` | `30.0` | Per-request timeout (seconds) |
| `max_retries` | `3` | Max retries for **idempotent** operations |
| `backoff_factor` | `0.5` | Exponential-backoff base multiplier (seconds) |
| `default_version` | `"v5"` | Version used by the `order` / `price` shortcuts |
| `default_headers` | `{}` | Extra headers added to every request |
| `user_agent` | `tronado-python/<ver>` | `User-Agent` header |
| `http_client` | `None` | Inject your own `httpx.Client`/`AsyncClient` |

```python
client = TronadoClient(
    api_key="YOUR_API_KEY",
    timeout=15.0,
    max_retries=5,
    backoff_factor=0.25,
    default_headers={"X-Trace-Id": "abc123"},
)
```

You can also pass a fully built `TronadoConfig`:

```python
from tronado import TronadoConfig, TronadoClient

config = TronadoConfig(api_key="YOUR_API_KEY", timeout=10)
client = TronadoClient(config=config)
```

---

## Quickstart (sync)

```python
from decimal import Decimal
from tronado import TronadoClient

with TronadoClient(api_key="YOUR_API_KEY") as tron:
    # 1. Tronado's TRX price differs from exchanges — always price first.
    price = tron.price.tron.get_price_to_toman()
    print(price.tron_price_toman, "Toman per TRX")

    # 2. Create the order and get a payment link.
    order = tron.order.get_order_token(
        payment_id="inv-1001",                       # your unique id
        wallet_address="TXYZ12345abcdef...",         # destination wallet
        tron_amount=Decimal("12.123456"),            # invoice amount in TRX
        callback_url="https://your-domain.com/payment/callback",  # registered domain
        wage_from_business_percentage=0,             # who absorbs the fee (0–100)
    )
    print("Pay here:", order.full_payment_url)
    # Or put this behind a button in your own bot: it opens Tronado's payment page
    # directly, without the customer having to start the Tronado bot.
    print("Payment page:", order.payment_page_url)

    # 3. Later, check status (by Tronado OrderId / TrndOrderID_x / TXID).
    status = tron.order.get_status(id="TrndOrderID_55")
    print("Paid?" , status.is_payment_accepted)
```

## Quickstart (async)

```python
import asyncio
from tronado import AsyncTronadoClient

async def main() -> None:
    async with AsyncTronadoClient(api_key="YOUR_API_KEY") as tron:
        price = await tron.price.tron.get_price_to_toman()
        order = await tron.order.get_order_token(
            payment_id="inv-1002",
            wallet_address="TXYZ...",
            tron_amount="8.5",
            callback_url="https://your-domain.com/payment/callback",
        )
        print(order.full_payment_url)

asyncio.run(main())
```

---

## Endpoint reference

The async client exposes the same methods with `await`.

### Order — `client.order`

| Method | Endpoint | Returns |
|---|---|---|
| `get_order_token(payment_id, wallet_address, tron_amount, callback_url, wage_from_business_percentage=0)` | `POST /api/v5/GetOrderToken` | `OrderTokenData` |
| `get_status(id)` | `POST /Order/GetStatus` | `OrderStatus` (raises `OrderNotFoundError` if absent) |
| `get_status_by_payment_id(id)` | `POST /Order/GetStatusByPaymentID` | `OrderStatus` |

`OrderTokenData.payment_page_url` builds the documented payment page deep link
(`https://t.me/tronado_robot/customerpayment?startapp={token}`).

### Price — `client.price`

Public endpoints: no API key is needed or sent. `get_price_with_wage_to_toman` is
authenticated by the `request_code` you get from support instead.

| Method | Endpoint | Returns |
|---|---|---|
| `price.tron.get_price_to_toman()` | `POST /Tron/GetPriceToToman` | `TronPrice` |
| `price.tron.get_price_with_wage_to_toman(request_code, wallet_address, tron_amount)` | `POST /Tron/GetPriceWithWageToToman` | `PriceWithWage` |
| `price.toman.convert_to_tron_wage_subtracted(toman, wallet)` | `POST /Toman/ConvertToTronWageSubtracted` | `TronConversion` |
| `price.dollar.convert_to_tron_wage_subtracted(dollar, wallet)` | `POST /Dollar/ConvertToTronWageSubtracted` | `TronConversion` |
| `price.dollar.get_price_to_toman()` | `POST /Dollar/GetPriceToToman` | `DollarPrice` |
| ~~`price.toman.get_price_to_toman()`~~ | `POST /Toman/GetPriceToToman` | `DollarPrice` — **deprecated**, no longer documented; use `price.dollar.get_price_to_toman()` |

> Amount arguments (`tron_amount`, `dollar`) accept `Decimal`, `int`, `float`, or `str`.
> They are coerced via `str` to avoid binary-float rounding, and sent on the wire as JSON
> numbers. Endpoints without input are sent an empty `{}` body, as the docs require (a
> POST with no body is rejected with `411 Length Required`).

---

## Order statuses

`OrderStatusID` is documented as a fixed set, used identically by `get_status` and the
webhook. The SDK exposes them as `tronado.OrderStatusCode`:

| `OrderStatusID` | `OrderStatusCode` | Meaning |
|---|---|---|
| `20` | `WAITING_FOR_PAYMENT` | Order created; awaiting the user's payment |
| `25` | `PHOTO_SENT_TO_ADMIN` | Payment proof submitted, sent to an admin |
| `27` | `READY_TO_TRANSFER` | Approved; queued for the on-chain TRX transfer |
| **`30`** | **`PAYMENT_ACCEPTED`** | **Successful, final payment (`IsPaid == true`)** |
| `40` | `PAYMENT_REJECTED` | Payment rejected |
| `200` | `CANCELLED` | Order cancelled |

Only **`30` (`PAYMENT_ACCEPTED`)** means money is settled — that's what
`is_payment_accepted` checks (alongside `IsPaid`). `OrderStatusTitle` is a Persian,
display-only label, so branch on the id, never the title.

```python
from tronado import OrderStatusCode

status = tron.order.get_status(id="TrndOrderID_55")
if status.is_payment_accepted:                 # IsPaid or OrderStatusID == 30
    fulfill()
elif status.order_status is OrderStatusCode.PAYMENT_REJECTED:
    notify_rejected()
# status.order_status is None for any id Tronado may add in future (no crash).
```

---

## Handling webhooks (IPN)

Tronado POSTs a JSON callback to your `CallbackUrl` **on every order status change** and
signs it with `X-Tronado-Sig = HMAC_SHA512(raw_body, your_ipn_signing_key)` (lowercase
hex). Get your `IpnSigningKey` from support. **Always verify against the raw body** — do
not re-serialize parsed JSON.

> **Register your callback domain.** The domain of `CallbackUrl` must be on your
> business's allow-list (ask support) and the URL must be `https`. If the domain is not
> registered, **no callback is sent** and the order silently stays pending on your side.

```python
from tronado.webhook import construct_event
from tronado.exceptions import InvalidSignatureError

IPN_SIGNING_KEY = "YOUR_IPN_SIGNING_KEY"

def handle_webhook(raw_body: bytes, signature_header: str) -> int:
    try:
        event = construct_event(raw_body, signature_header, IPN_SIGNING_KEY)
    except InvalidSignatureError:
        return 401  # reject

    # De-duplicate: the same (payment_id, status) may arrive more than once.
    if already_processed(event.dedup_key):
        return 200

    if event.is_payment_accepted:               # IsPaid == True or status 30
        # Default wage mode (0): credit the Toman value of the TRX you received.
        # See "Which amount to credit" below for the other modes.
        credit_user(event.payment_id, event.toman_amount_without_wage)

    return 200  # return 2xx to acknowledge, else Tronado retries
```

### Which amount to credit

The two v5 Toman fields mean different things: `toman_amount_without_wage` is the Toman
value of the TRX actually delivered to you; `user_paid_toman_amount` is what the user
paid, **including** the fee. Pick by the `wage_from_business_percentage` you used:

| `wage_from_business_percentage` | Credit the user with |
|---|---|
| `0` (default — the user pays the fee) | `toman_amount_without_wage`. Crediting `user_paid_toman_amount` here gifts Tronado's fee to the user out of your pocket. |
| `100` (you absorb the fee) | `user_paid_toman_amount` (≈ your invoice's base value) |
| between `0` and `100` | your own invoice value: the `tron_amount` you sent to `get_order_token` × the TRX price |

The TRX price in a given order is `toman_amount_without_wage ÷ tron_amount`, available as
`event.tron_price_toman`.

FastAPI example (reads the **raw** body before parsing):

```python
from fastapi import FastAPI, Request, Response
from tronado.webhook import construct_event
from tronado.exceptions import InvalidSignatureError, TronadoWebhookError

app = FastAPI()

@app.post("/payment/callback")
async def callback(request: Request) -> Response:
    raw = await request.body()
    sig = request.headers.get("X-Tronado-Sig", "")
    try:
        event = construct_event(raw, sig, "YOUR_IPN_SIGNING_KEY")
    except (InvalidSignatureError, TronadoWebhookError):
        return Response(status_code=401)
    # ... process event ...
    return Response(status_code=200)
```

If you only need to verify or parse separately:

```python
from tronado.webhook import verify_signature, parse_callback

if verify_signature(raw, sig, signing_key):
    event = parse_callback(raw)
```

---

## Handling dispute callbacks

After an order is approved, the card holder can dispute it (e.g. "no deposit was made",
"less was deposited"). When Tronado **accepts** a dispute the order is either annulled or
its amount corrected, and an optional, signed **dispute callback** tells you so.

- **Opt-in**, sent to a separate `DisputeCallbackUrl`, never the order's `CallbackUrl`.
  Set it in the Tronado mini app under
  [Business → Settings](https://miniapp.tronado.cloud/business/settings) (or via
  support). Its domain must be on the same callback allow-list.
- Signed exactly like the IPN: same `X-Tronado-Sig` header, same `IpnSigningKey`.
- Sent only for **accepted** disputes of a type that affects your order.
- Delivered **at least once**: de-duplicate on `event.dedup_key` (`DisputeId`).
- Acknowledge with 2xx. Transient failures (5xx, 408, 429, timeout) are retried up to 10
  more times over ~4.5 hours; permanent 4xx (e.g. 404, 410) are not retried. So answer
  5xx when *your* side fails temporarily.

Branch on the **outcome**, not the dispute type:

| Outcome | Meaning | What to do |
|---|---|---|
| `Annulled` (`event.is_annulled`) | The money never arrived, or the receipt was a duplicate; the order is cancelled. | Reverse what you granted for `event.payment_id` (like a chargeback). |
| `AmountAdjusted` (`event.is_amount_adjusted`) | The user paid a different amount; the order was corrected to it. | Adjust the balance by `event.user_must_pay_toman_delta` / `event.tron_amount_delta`. |
| anything else (`NoChange` is reserved) | Reserved for the future. | Log it; no action. |

An annulled order also triggers the regular IPN with `OrderStatusID == 200`. The two may
arrive in either order, and processing both is safe.

```python
from tronado.webhook import construct_dispute_event
from tronado.exceptions import InvalidSignatureError, TronadoWebhookError

def handle_dispute(raw_body: bytes, signature_header: str) -> int:
    try:
        event = construct_dispute_event(raw_body, signature_header, IPN_SIGNING_KEY)
    except InvalidSignatureError:
        return 401
    except TronadoWebhookError:
        return 400  # signed, but not a valid dispute payload

    # Acknowledge (but ignore) future event types and repeated deliveries.
    if not event.is_dispute_accepted or already_processed(event.dedup_key):
        return 200

    if event.is_annulled:
        reverse_credit(event.payment_id)
    elif event.is_amount_adjusted:
        adjust_credit(event.payment_id, event.user_must_pay_toman_delta)
    else:
        log.info("Unhandled dispute outcome %s", event.outcome)
    return 200
```

The payload carries no card-holder identity, dispute text or receipt, only the effect on
your order. `DisputeTypeCode` and `DisputeOutcome` enumerate the documented values.

---

## Error handling

All errors derive from `TronadoError`:

```python
from tronado.exceptions import (
    TronadoError, TronadoAuthenticationError, TronadoRateLimitError,
    OrderNotFoundError, TronadoValidationError, TronadoServerError,
    TronadoTimeoutError, TronadoConnectionError,
)

try:
    status = client.order.get_status(id="maybe-missing")
except OrderNotFoundError:
    status = None
except TronadoAuthenticationError:
    ...   # bad/missing API key (HTTP 401 or envelope Code == -1)
except TronadoRateLimitError:
    ...   # 429 / per-user limits
except (TronadoTimeoutError, TronadoConnectionError):
    ...   # network problems
except TronadoServerError:
    ...   # 5xx (already retried for idempotent calls)
except TronadoError:
    ...   # catch-all
```

`TronadoAPIError` (and its subclasses) carry `.status_code`, `.code`, `.message`, and
`.response` for diagnostics.

### Retries & idempotency

- Idempotent reads (price/status) are retried on timeouts, connection errors, `429`, and
  `5xx`, using exponential backoff with jitter (and `Retry-After` when present).
- **`get_order_token` is never auto-retried** — it creates a transaction, so retrying on
  an ambiguous failure could create a duplicate order. Handle its failures explicitly.

---

## Versioning

The Tronado API versions endpoints in the URL path (`/api/v{version}/...`). In v5 only
`GetOrderToken` is version-pathed; the price/status endpoints live at unversioned roots.
The SDK models this with per-version **operation descriptors**, so:

```python
client.v5.order.get_order_token(...)     # explicit version pin
client.version("v5").price.tron.get_price_to_toman()
client.order.get_order_token(...)        # uses default_version
```

When Tronado ships a new version, it becomes a new `tronado/versions/vN/` package and a
one-line registry entry — the transport, models, and error handling are reused unchanged.

```python
from tronado import available_versions
print(available_versions())   # ('v5',)
```

---

## The fee (wage) model

The default wage is 20% (configurable per business; minimum is the greater of 9,000 Toman
or $0.10). `wage_from_business_percentage` on `get_order_token` controls who absorbs it:

- `0` (default): the whole fee is added on top of the user's payment; you receive the full
  invoice TRX.
- `100`: the whole fee is taken from your share; the user pays roughly the base value and
  your received `TronAmount` is the net after fee.
- Values in between split the fee proportionally.

Worked example from the docs: a 10 TRX invoice, a 20% wage, 70,000 Toman per TRX
(network fee ignored):

| `wage_from_business_percentage` | TRX you receive | `TomanAmountWithoutWage` | `UserPaidTomanAmount` |
|---|---|---|---|
| `0` | 10.000 | 700,000 | 840,000 |
| `50` | 9.167 | 641,700 | 770,000 |
| `100` | 8.333 | 583,300 | 700,000 |

The percentage decides how much TRX you get, not which field to credit; see
[Which amount to credit](#which-amount-to-credit). Real amounts differ by up to a few
thousand Toman because of rounding and a small amount added to make each deposit unique.

**TRON network fee:** for NowPayments wallets or inactive wallets, about 1.2 TRX (wallet
activation) is added to the final amount; for active wallets, the transfer fee (up to
about 0.8 TRX) is added. Contact support if more than that is added.

## Limits

Per-user transaction limits, as documented:

| Limit | Value | Adjustable? |
|---|---|---|
| Transactions per day | 1 | via support |
| Daily amount | 500,000 Toman | yes |
| Monthly amount | 1,000,000 Toman | via support |
| Cancelled transactions per day | 2 | no |
| Cancelled transactions per month | 4 | no |

## Testing your callback

From the Telegram account your business is registered with, send the Tronado bot one of
these (for localhost, expose a public URL with a tunnel and use it as the callback URL):

```text
/dummyrequest <your_callback_url>
```

```text
/dummysuccessfulrequest {
  "PaymentID": "12345",
  "UserTelegramId": 123456,
  "Wallet": "Wallet",
  "TronAmount": 12.123456,
  "ActualTronAmount": 12.123456,
  "CallbackUrl": "https://your-tunnel.example.com/Test/Test"
}
```

---

## Development

```bash
pip install -e ".[dev]"
pytest                 # run the test-suite (sync + async)
ruff check .           # lint
mypy src               # type-check
```

Run the suite across every supported interpreter with **tox** (included in the `dev`
extra installed above):

```bash
tox                    # py39–py313 + a lint/type-check env
```

CI (GitHub Actions, [`.github/workflows/ci.yml`](.github/workflows/ci.yml)) runs ruff and
mypy once, then the test-suite on Python **3.9, 3.10, 3.11, 3.12, and 3.13**.

See [`examples/`](examples/) for runnable scripts and [`docs/DESIGN.md`](docs/DESIGN.md)
for the architecture and the full endpoint matrix.

## License

MIT — see [LICENSE](LICENSE).

Support: [t.me/TronadoSupp](https://t.me/TronadoSupp)
