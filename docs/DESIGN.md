# Tronado Python SDK — Design & Endpoint Matrix

> Status: approved design (2026-06-23), updated 2026-09-23. Source of truth: the
> official Tronado API docs, <https://miniapp.tronado.cloud/assets/api-docs.md>
> (version **v5**; this replaced the earlier Postman collection).

## 1. Source facts extracted from the documentation

- **Base URL:** `https://bot.tronado.cloud`
- **Authentication:** API key sent in the HTTP header **`x-api-key`** (lowercase).
  There is **no** `Authorization: Bearer` scheme. The order endpoints require it. The
  price endpoints are **public** and do not; `GetPriceWithWageToToman` is authenticated
  by `RequestCode` in its body instead. The SDK therefore only sends (and only requires)
  the key for operations flagged `requires_auth`.
- **Content type:** `application/json` on every request. Every POST carries a body:
  endpoints without input are sent `{}`, because IIS rejects a POST without a
  `Content-Length` with `411 Length Required` (easily mistaken for a 404).
- **Versioning:** the version segment appears in the URL path as `/api/v{version}/...`.
  Current recommended version: **v5**. *Only* the `GetOrderToken` endpoint is
  version-pathed (`/api/v5/GetOrderToken`); every other endpoint lives at an
  **unversioned** root (`/Order/...`, `/Tron/...`, `/Toman/...`, `/Dollar/...`).
- **Response envelope:** `GetOrderToken` returns an envelope
  `{ "IsSuccessful": bool, "Code": int, "Message": str, "Data": {...} }`.
  All other endpoints return a **flat** object. `GetStatus` signals "not found" as
  **HTTP 200** with body `{ "Error": "No order found with this txid" }`.
- **Callback domain allow-list:** the `CallbackUrl` domain must be registered with
  support and the URL must be `https`; otherwise **no** callback is sent at all.
- **Webhook (IPN) signature — explicitly documented:** Tronado POSTs each status
  change to your `CallbackUrl` with header
  `X-Tronado-Sig = HMAC_SHA512(rawJsonBody, YOUR_IPN_SIGNING_KEY)` rendered as
  lowercase hex, computed over the **raw** request body before parsing, compared in
  constant time. The docs include Node.js (`crypto.createHmac('sha512', …)`) and C#
  (`HMACSHA512`) reference implementations. This SDK implements exactly that scheme.
- **Order status:** the docs define a fixed `OrderStatusID` set, used identically by the
  `GetStatus` response and the IPN callback: `20 WaitingForPayment`, `25 PhotoSentToAdmin`,
  `27 ReadyToTransfer`, `30 PaymentAccepted`, `40 PaymentRejected`, `200 Cancelled`. Only
  `30` means a successful, final payment (`IsPaid == true`). `OrderStatusTitle` is a
  Persian, display-only label — branch on the id, not the title. The SDK models these as
  `OrderStatusCode` and treats any *undocumented* id as unknown rather than guessing.
- **Which webhook amount to credit:** `TomanAmountWithoutWage` is the Toman value of the
  TRX delivered to the business; `UserPaidTomanAmount` is what the user paid, fee
  included. With `wageFromBusinessPercentage = 0` (default) credit the former; with `100`
  the latter; in between, the business's own invoice value (invoice TRX × TRX price,
  where the per-order price is `TomanAmountWithoutWage ÷ TronAmount`).
- **Dispute callback (opt-in):** when a dispute on an approved order is *accepted*,
  Tronado POSTs a `DisputeAccepted` event to a separate `DisputeCallbackUrl` (set in the
  mini app, same domain allow-list), signed exactly like the IPN. Delivery is at least
  once (de-duplicate on `DisputeId`); transient failures (5xx/408/429/timeout) are
  retried up to 10 times over ~4.5 h, permanent 4xx are not. `Outcome` is `Annulled` or
  `AmountAdjusted` (`NoChange` reserved; unknown values are log-only). An annulled order
  also gets the normal IPN with `OrderStatusID == 200`, in no guaranteed order.
  `DisputeTypeID`: `1 NoDeposit`, `11 AmountIsInRial`, `31 AmountIsMore`,
  `41 AmountIsLess`, `61 ReceiptIsRepetitive`.
- **Payment page:** `https://t.me/tronado_robot/customerpayment?startapp={Token}` opens
  the payment mini app directly from a button in the business's own bot.
- **Per-user limits (informational):** 1 tx/day, 500k toman/day, 1M toman/month,
  2 cancelled/day, 4 cancelled/month.

## 2. Endpoint matrix

| Resource.method | HTTP | Path | Auth | Request fields (JSON, PascalCase) | Response fields | Documented error shape |
|---|---|---|---|---|---|---|
| `order.get_order_token` | POST | `/api/v5/GetOrderToken?wageFromBusinessPercentage={0..100}` | `x-api-key` | `PaymentID` str, `WalletAddress` str, `TronAmount` decimal, `CallbackUrl` https str | envelope → `Data`: `Token`, `FullPaymentUrl`, `ErrorMessage`, `EstimatedTomanAmount` str, `EstimatedTomanAmountExpireDateUtc` datetime | `401` envelope `{IsSuccessful:false, Code:-1, Message, Data:null}`; business failure → `IsSuccessful:false` |
| `order.get_status` | POST | `/Order/GetStatus` | `x-api-key` | `Id` str (Tronado OrderId / `TrndOrderID_{id}` / TXID) | `UniqueCode`, `PaymentID`, `UserTelegramId` long, `Wallet`, `Hash`, `TronAmount` dec, `ActualTronAmount` dec?, `OrderStatusID` int?, `OrderStatusTitle`, `IsPaid` bool, `PaymentDate` | `200` `{"Error":"No order found with this txid"}` → `OrderNotFoundError` |
| `order.get_status_by_payment_id` | POST | `/Order/GetStatusByPaymentID` | `x-api-key` | `Id` str (= your `PaymentID`) | same as `get_status` | same as `get_status` |
| `price.tron.get_price_to_toman` | POST | `/Tron/GetPriceToToman` | none | `{}` | `TronPriceToman` int, `TronPriceDollar` dec | — |
| `price.tron.get_price_with_wage_to_toman` | POST | `/Tron/GetPriceWithWageToToman` | `RequestCode` in body | `RequestCode` str, `WalletAddress` str, `TronAmount` dec | `ActualAmountToman` int, `AmountWithWageToman` int | — |
| `price.toman.convert_to_tron_wage_subtracted` | POST | `/Toman/ConvertToTronWageSubtracted` | none | `Toman` int, `Wallet` str | `TronAmount` dec, `TronSunAmount` dec | — |
| `price.dollar.convert_to_tron_wage_subtracted` | POST | `/Dollar/ConvertToTronWageSubtracted` | none | `Dollar` dec, `Wallet` str | `TronAmount` dec, `TronSunAmount` dec | — |
| `price.dollar.get_price_to_toman` | POST | `/Dollar/GetPriceToToman` | none | `{}` | `DollarPrice` int | — |
| ~~`price.toman.get_price_to_toman`~~ *(deprecated)* | POST | `/Toman/GetPriceToToman` | none | `{}` | `DollarPrice` int | no longer documented (still answers); emits `DeprecationWarning` |
| **IPN webhook (inbound)** | POST → you | your `CallbackUrl` | `X-Tronado-Sig` (HMAC-SHA512 hex) | `UniqueCode`, `PaymentId`, `UserTelegramId`, `Wallet`, `Hash`, `TronAmount`, `ActualTronAmount`, `UserPaidTomanAmount` (v5), `TomanAmountWithoutWage` (v5), `OrderStatusID`, `OrderStatusTitle`, `IsPaid`, `PaymentDate` | invalid signature → reject (`InvalidSignatureError`) |
| **dispute webhook (inbound, opt-in)** | POST → you | your `DisputeCallbackUrl` | `X-Tronado-Sig` (same key) | `Event`, `EventId`, `DisputeId`, `DisputeType`, `DisputeTypeID`, `DisputeTypeTitle`, `Outcome`, `UniqueCode`, `PaymentId`, `RaisedAt`, `ResolvedAt`, `OriginalTronAmount`, `OriginalUserMustPayToman`, `TronAmount`, `UserMustPayToman`, `TronAmountDelta`, `UserMustPayTomanDelta`, `OrderStatusID`, `OrderStatusTitle`, `IsPaid` | invalid signature → `InvalidSignatureError`; missing `Event`/`DisputeId` → `TronadoWebhookError` |

> Note the field-name inconsistency the SDK normalizes: status responses use
> `PaymentID`, the webhook payload uses `PaymentId`. Both map to the Python field
> `payment_id`.

## 3. Architecture

Layered, version-aware:

```
config ─► transport (core HTTP, retries, error mapping) ─► versions ─► resources ─► models
                                   ▲                                                  │
                                   └───────────────────── exceptions ◄───────────────┘
webhook (standalone inbound verifier + parser)
```

- `tronado.config.TronadoConfig` — immutable settings.
- `tronado._http` — `SyncTransport` / `AsyncTransport` over **httpx**; share **pure**
  helpers for request preparation, retry decisions and response processing, so no
  business logic is duplicated between sync and async (only the imperative loop and
  the `time.sleep` / `asyncio.sleep` call differ).
- `tronado.versions` — a registry mapping a version tag to a `Version` object built
  from `Operation` descriptors (method, path template, request/response models,
  envelope handling, not-found key, **idempotent** and **requires_auth** flags). Adding v6 = a new
  `versions/v6/` package + registry entry; nothing else changes.
- `tronado.versions.v5.resources` — typed resource facades grouped like the docs:
  `order`, `price.tron`, `price.toman`, `price.dollar`.
- `tronado.models` — Pydantic v2 models with PascalCase aliases, `Decimal` for all
  amounts (never `float`), tolerant datetime parsing.
- `tronado.exceptions` — single hierarchy.
- `tronado.webhook` — `verify_signature`, `parse_callback` / `construct_event` (IPN),
  `parse_dispute_callback` / `construct_dispute_event` (dispute callback).

## 4. Retry & idempotency policy

- Retryable transport failures: connection errors, timeouts, HTTP `429`, `5xx`.
- Retries use exponential backoff with jitter (`backoff_factor`, `max_backoff`),
  honoring `Retry-After` when present.
- **Idempotency:** `GetOrderToken` is flagged **non-idempotent** — it creates a
  transaction, so it is **never auto-retried** (not even on connection errors) to
  avoid duplicate orders. All price/status reads are idempotent and retried.

## 5. Error model

`get_status` "not found" raises `OrderNotFoundError`. HTTP `401` / envelope
`Code == -1` → `TronadoAuthenticationError`. `429` → `TronadoRateLimitError`. `5xx`
(after retries) → `TronadoServerError`. Envelope `IsSuccessful == false` →
`TronadoValidationError`. Network → `TronadoConnectionError` / `TronadoTimeoutError`.
Webhook signature mismatch → `InvalidSignatureError`. Calling an authenticated
operation without an API key → `TronadoConfigError`, raised before any request is sent.

## 6. Out of scope / not invented

- No status codes beyond the six documented in `OrderStatusCode`
  (`20/25/27/30/40/200`); only `30 = PaymentAccepted` is treated as paid. Likewise the
  dispute enums (`DisputeEvent`, `DisputeTypeCode`, `DisputeOutcome`) hold only the
  documented values; anything else maps to `None` rather than raising.
- No helper that picks the webhook amount to credit: the right field depends on the
  wage percentage the business used, so the SDK documents the rule instead of guessing.
- No auth scheme other than the documented `x-api-key` header.
- The webhook signature scheme is implemented **only** because the docs define it
  explicitly; if a future version removed that definition, `verify_signature` would
  be the only thing to gate behind a capability flag.
