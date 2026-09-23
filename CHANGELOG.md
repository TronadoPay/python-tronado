# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-09-23

Aligned with the updated official API docs
(<https://miniapp.tronado.cloud/assets/api-docs.md>), which replace the Postman collection.

### Added

- Dispute callback support: `DisputeCallbackPayload`, `parse_dispute_callback` and
  `construct_dispute_event` (same `X-Tronado-Sig` scheme and key as the IPN), plus the
  `DisputeEvent`, `DisputeTypeCode` and `DisputeOutcome` enums. The payload exposes
  `is_annulled`, `is_amount_adjusted`, `dedup_key` (`DisputeId`) and typed deltas.
- `OrderTokenData.payment_page_url`: the documented payment page deep link
  (`https://t.me/tronado_robot/customerpayment?startapp={token}`), also available as
  `PAYMENT_PAGE_URL_TEMPLATE`.
- `CallbackPayload.tron_price_toman`: the per-order TRX price,
  `TomanAmountWithoutWage ÷ TronAmount`.
- `Operation.requires_auth` and `TronadoConfig.build_headers(authenticated=...)`.

### Changed

- The price endpoints are documented as public: the SDK no longer sends the API key to
  them, and a client can be built without a key. `TronadoConfigError` for a missing key
  is now raised when an order endpoint is called (still before any request is sent)
  instead of at construction. A blank key is treated as missing.
- Endpoints without input now send an explicit `{}` body, as the docs require (IIS
  rejects a POST without a body with `411 Length Required`).
- Corrected the webhook guidance: in the default wage mode (`0`) credit
  `toman_amount_without_wage`, not `user_paid_toman_amount` (that would gift Tronado's
  fee to the user). Docstrings, README and examples now carry the documented table for
  each wage mode.
- README: callback domain allow-list, the fee worked example, the TRON network fee,
  limits, and the `/dummyrequest` testing commands.

### Deprecated

- `price.toman.get_price_to_toman()` (`/Toman/GetPriceToToman`) is no longer documented.
  It still works but emits a `DeprecationWarning`; use `price.dollar.get_price_to_toman()`,
  which returns the same `DollarPrice`.

## [0.1.1] - 2026-06-24

### Added

- `OrderStatusCode` now covers the full documented `OrderStatusID` set —
  `20 WaitingForPayment`, `25 PhotoSentToAdmin`, `27 ReadyToTransfer`,
  `30 PaymentAccepted`, `40 PaymentRejected`, `200 Cancelled` — matching the updated
  Postman docs (previously only `30` was modelled).
- `OrderStatus.order_status` and `CallbackPayload.order_status` properties map the raw
  `OrderStatusID` to `OrderStatusCode`, returning `None` for any undocumented id
  (forward compatible).

### Changed

- `TronadoConfig` is now frozen/immutable, including a read-only `default_headers`.
- `Content-Type: application/json` is sent on every request (including the no-body price
  endpoints), matching the documented contract.
- `wage_from_business_percentage` is validated to the 0–100 range locally before sending.
- `CallbackPayload.payment_id` accepts both `PaymentId` and `PaymentID` spellings.

### Notes

- `is_payment_accepted` continues to treat only status `30` (`PaymentAccepted`) — or
  `IsPaid == true` — as a settled payment.
- Added `tox` config and a GitHub Actions matrix covering Python 3.9–3.13.

## [0.1.0] - 2026-06-23

### Added

- Initial release with full coverage of the Tronado Public API **v5**.
- Synchronous `TronadoClient` and asynchronous `AsyncTronadoClient` (built on `httpx`).
- Version-aware architecture (`tronado.versions`) with v5 implemented; new versions plug
  in via the registry without touching the transport, models, or error handling.
- Typed Pydantic v2 request/response models with PascalCase aliasing and `Decimal`
  amounts.
- `Order` resource: `get_order_token`, `get_status`, `get_status_by_payment_id`.
- `price` namespace: `tron`, `toman`, and `dollar` price/conversion endpoints.
- Inbound IPN/webhook helpers: `verify_signature`, `parse_callback`, `construct_event`
  implementing the documented HMAC-SHA512 (`X-Tronado-Sig`) scheme.
- Configurable base URL, timeout, retries (exponential backoff with jitter, `Retry-After`
  aware), and default headers.
- Idempotency-aware retries: `GetOrderToken` is never auto-retried (it creates a
  transaction); reads are retried.
- Full exception hierarchy rooted at `TronadoError`.
- Unit test-suite (sync + async) and runnable examples.
