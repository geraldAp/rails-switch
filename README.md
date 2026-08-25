# RailSwitch

RailSwitch is a **framework-agnostic Python payment orchestration and scaffolding project**.

It lets you scaffold an **owned, framework-neutral payment module** into your own Python application. The CLI generates source that lives in your codebase — you call `PaymentService` internally from your own domain code. FastAPI is **not** required by RailSwitch; this repository includes a FastAPI example app only to demonstrate one host integration.

It is an early MVP, not a full blown production-ready payment platform but it stills gives you the chance to build something production ready on top of it .

## Core architecture

```text
Host application route / domain logic
            ↓
    Application service  e.g. OrderService
            ↓
      PaymentService
            ↓
  PaymentProviderFactory  (Country -> set[PaymentProvider])
            ↓
      Provider adapter  (Paystack / Bachs / Stripe)
            ↓
       Provider API
```

Host code never needs to expose generic RailSwitch HTTP endpoints. Call `PaymentService.collect/disburse/verify` directly.

## CLI usage

PyPI package: `railswitch-payments`
CLI command: `railswitch`

Run without installing:

```bash
uvx --from railswitch-payments railswitch init
uvx --from railswitch-payments railswitch init --path app/modules/payments
uvx --from railswitch-payments railswitch init --providers paystack
uvx --from railswitch-payments railswitch init --providers paystack stripe
uvx --from railswitch-payments railswitch init --providers paystack --countries GH
uvx --from railswitch-payments railswitch init --countries NG
```

Behavior:

* No `--providers` and no `--countries` → all providers, all their supported countries.
* `--providers` with no `--countries` → all countries supported by the selected providers.
* `--countries` alone infers provider(s) where the mapping is currently unambiguous (`GH`→`paystack`, `NG`→`bach`, `CA`→`stripe`, `GH CA`→`paystack, stripe`).
* Duplicate inputs are deduplicated preserving first occurrence (`--providers stripe stripe paystack` → `stripe, paystack`).
* Only selected provider folders, config fields, env sections, dependency imports, and factory routes are generated.

Implementation source of truth: `src/railswitch_cli/cli.py` (`ProviderDefinition`, `ProviderCountryDefinition`, `SelectedProviderDefinition`).

## Current providers / countries

| Provider | Countries | Codes |
|---|---|---|
| **Paystack** | Ghana, South Africa | `GH`, `ZA` |
| **Bachs** | Nigeria | `NG` |
| **Stripe** | United States, Canada | `US`, `CA` |

Operations via `PaymentService`:

* **Hosted checkout collection** — all three providers (`collect`)
* **Disbursement** — Paystack (transfer) and Bachs (bank-account payout) where provider matches contract; **Stripe `disburse()` intentionally raises** `ValueError: Stripe payout creation is unsupported` (`examples/fastapi/app/payments/providers/stripe/provider.py:32`)
* **Verification** — collection or disbursement (`verify` requires explicit `provider` + `provider_reference`)

## Generated module

```text
payments/
├── __init__.py
├── config.py        # generated - only selected country/provider fields + dynamic comment
├── contracts.py     # shared dataclasses + PaymentProvider ABC
├── dependencies.py  # generated - build_payment_service() / get_payment_service()
├── enums.py
├── errors.py
├── factory.py       # generated - ROUTES + PaymentProviderFactory
├── service.py       # PaymentService
└── providers/
    └── selected providers only  (paystack | bach | stripe)
```

* `contracts.py`, `service.py`, `errors.py`, `enums.py` and `providers/<name>/` are framework-neutral with relative imports — custom `--path` works (`app/modules/payments`).
* `config.py`, `dependencies.py`, `factory.py` are generated dynamically from selected capabilities. Factory routes, config comments/fields, env sections, and helper functions reflect only the selected provider-country combinations.

## Provider-country capability routing

Runtime routing in the reference app’s `examples/fastapi/app/payments/factory.py:5`:

```python
ROUTES = {
    Country.GHANA: {Provider.PAYSTACK},
    Country.SOUTH_AFRICA: {Provider.PAYSTACK},
    Country.NIGERIA: {Provider.BACH},
    Country.UNITED_STATES: {Provider.STRIPE},
    Country.CANADA: {Provider.STRIPE},
}
# generated ROUTES contains only selected countries
```

Rules (`PaymentProviderFactory.get_provider(country, provider=None)`):

* `country` is required.
* `provider` is optional for `collect`/`disburse`; required for `verify`.
* If `provider is None` and exactly one configured provider exists for `country` → use it.
* If multiple providers are configured for `country` → caller must specify `provider`, otherwise `ValueError: Multiple providers are configured for country ...; specify a provider`.
* If explicit `provider` is not in the country's set → `ValueError: Provider '...' is not configured for country ...`.
* If country has no route → `ValueError: No generated provider is configured for country ...`.
* If provider was not generated (dict miss) → `ValueError: Provider '...' was not generated`.

Example (`GH -> {PAYSTACK}`):

```
country=GH, provider=None      → Paystack
country=GH, provider=PAYSTACK  → Paystack
country=GH, provider=STRIPE    → rejected (not configured for GH)
```

Designed to support multiple providers per country later without a default-provider priority in v0.1.

## Payment contracts

Reference contract: `examples/fastapi/app/payments/contracts.py`:

**CheckoutRequest**
* `country: Country`, `amount_minor: int`, `currency: Currency`, `email: str`
* Optional: `provider: PaymentProvider | None`, `payment_methods`, `reference`, `metadata`, `customer_name`

**DisbursementRequest**
* `country`, `amount_minor`, `currency`, `method: DisbursementMethod`, `account_number`, `bank_code`
* Optional: `account_name`, `provider`, `reference`, `metadata`

**VerificationRequest**
* `provider_reference: str`, `provider: PaymentProvider`, `country: Country`, `operation: PaymentOperation`

Responses (`CheckoutResponse`, `DisbursementResponse`, `VerificationResponse`) carry `reference`, `provider_reference`, `provider`, `status`, plus provider-specific fields (`checkout_url`, `method`, `amount_minor`). `raw_response` is internal.

## Reference vs provider_reference

* `reference` — caller/application correlation ID. Host owns it. For orders: `order_id` becomes `CheckoutRequest.reference` and `metadata={"order_id": order_id}` (`examples/fastapi/app/orders/service.py:47`). If omitted, adapters generate `railswitch-<uuid>`.
* `provider_reference` — identifier used to retrieve/verify with the provider (Paystack transfer reference, Bachs `checkout_id`, Stripe `checkout_session_id`). Required for `verify`.

Keeping both lets the host preserve business context without pushing `order_id` into the payment layer.

## Configuration / environment

`app/payments/config.py` (`PaymentSettings` via `pydantic-settings`, `env_file=".env"`) is generated per selection. `.env.example` is updated (preserving existing content); `.env` is **never** modified. Generated runtime deps (`httpx2`, `pydantic-settings`) are installed via `uv add` when `uv` is available (`src/railswitch_cli/cli.py:499`).

Example `--providers paystack --countries GH`:

```env
PAYSTACK_GH_SECRET_KEY=
PAYSTACK_CALLBACK_URL=
# PAYSTACK_ZA_SECRET_KEY= is not generated/required
```

Other selections:

```env
# --providers stripe
STRIPE_SECRET_KEY=
STRIPE_SUCCESS_URL=
STRIPE_CANCEL_URL=

# --providers bach  (NG)
BACH_API_KEY=
BACH_BASE_URL=https://sandbox-api.bachs.io
```

Full set when all selected: `PAYSTACK_GH_SECRET_KEY`, `PAYSTACK_ZA_SECRET_KEY`, `PAYSTACK_CALLBACK_URL`, `BACH_API_KEY`, `BACH_BASE_URL`, `STRIPE_SECRET_KEY`, `STRIPE_SUCCESS_URL`, `STRIPE_CANCEL_URL`. Per-country helpers (e.g. `_paystack_secrets()`) are generated only for selected countries and validate missing credentials with `ValueError`.

## Example integration: FastAPI

> This is an example host, not a requirement. RailSwitch works with any Python framework.

The reference app at `examples/fastapi/app/main.py` mounts `order_router` (`/orders`), not a generic payment router. Run it from `examples/fastapi/` with `uv run uvicorn app.main:app --reload`.

**Route:** `POST /orders/{order_id}/checkout` (`examples/fastapi/app/api/routes/order.py:15`)

**Flow:**

```text
OrderCheckoutRequest  (HTTP, examples/fastapi/app/api/schemas/orders.py)
        ↓
OrderService  (examples/fastapi/app/orders/service.py, injected via examples/fastapi/app/orders/dependencies.py:get_order_service → get_payment_service @lru_cache)
        ↓
CheckoutRequest  (reference=order_id, metadata={"order_id": order_id}, provider optional)
        ↓
PaymentService.collect  (examples/fastapi/app/payments/service.py:18)
        ↓
Provider adapter
        ↓
CheckoutResponse  (internal)
        ↓
OrderCheckoutResult  (@dataclass(slots=True), 6 fields, examples/fastapi/app/orders/service.py:14)
        ↓
OrderCheckoutResponse  (HTTP, examples/fastapi/app/api/schemas/orders.py:22 - 4 fields, provider fields intentionally not exposed)
```

* `OrderCheckoutRequest`: `country, currency, amount_minor, email, customer_name?, payment_methods?, provider?` (`PaymentProvider | None`)
* `OrderCheckoutResponse`: `order_id, reference, status, checkout_url` — intentionally **does not** expose `provider`/`provider_reference` (they remain in `OrderCheckoutResult`).

**Example:**

```bash
curl -X POST http://127.0.0.1:8000/orders/ord_123/checkout \
  -H 'Content-Type: application/json' \
  -d '{
    "country": "GH",
    "currency": "GHS",
    "amount_minor": 5000,
    "email": "customer@example.com",
    "customer_name": "Customer Example",
    "payment_methods": ["card", "mobile_money"],
    "provider": "paystack"
  }'
```

Response `200`:

```json
{
  "order_id": "ord_123",
  "reference": "ord_123",
  "status": "pending",
  "checkout_url": "https://checkout.paystack.com/..."
}
```

`provider` in the request is optional; when omitted, factory selects the sole provider for the country. `ValueError` from routing/config maps to `422` via `HTTPException` in the route; `PaymentProviderError` maps via `@app.exception_handler` in `examples/fastapi/app/main.py:15`.

## Errors

`examples/fastapi/app/payments/errors.py:PaymentProviderError` normalizes provider/network failures. Public shape (`public_detail()`):

```json
{
  "detail": {
    "provider": "stripe",
    "operation": "collection",
    "category": "validation",
    "code": "parameter_invalid_empty",
    "message": "Stripe rejected the checkout request.",
    "retryable": false
  }
}
```

`category`: `validation` (422), `authentication`, `forbidden`, `not_found` (404), `conflict` (409), `insufficient_funds`, `rate_limited` (429), `processor`, `provider_unavailable` (502), `unknown`. `raw_response` stays internal, never exposed.

## Development vs user installation

**Users** — scaffold into your app:

```bash
uvx --from railswitch-payments railswitch init --providers paystack --countries GH
```

No clone needed. Generated code is yours to own.

**Contributors** — work on RailSwitch itself:

```bash
git clone https://github.com/geraldAp/rails-switch.git
cd rails-switch
uv sync
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

## Adding providers

Reflects current metadata architecture (`src/railswitch_cli/cli.py:22`):

1. Implement `providers/<name>/{client.py, mapper.py, provider.py, types.py}` against `PaymentProvider` (`collect`/`disburse`/`verify`).
2. Add `ProviderDefinition` with `country_capabilities` (`ProviderCountryDefinition` per `code`/`enum_name`, `config_fields`, `environment_variables`, `credential_setting`) plus `shared_environment_variables`, `shared_config_fields`, `dependency_imports`, `service_construction`, `helper_functions`.
3. Add routing capability — `country_capabilities` drive generated `ROUTES`; no fixed `paystack=`/`bach=` constructor.
4. Add mapper/client/provider/routing tests.

Keep provider details out of `PaymentService`; keep layers small.

## Status and limitations

Early open-source, not completely production-ready. Missing intentionally: payment persistence, webhooks, reconciliation, retries/circuit breakers, production hardening. Bachs defaults to sandbox. DB/Alembic scaffolding exists but payments are not persisted. Documented operations above are implemented; missing areas are not bugs.

## License

MIT — see `LICENSE`.
