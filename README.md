# RailSwitch

RailSwitch is a **framework-agnostic Python payment orchestration and scaffolding project**. It gives a host application a normalized `PaymentService` and scaffolds the payment module **into the host's own codebase** via a CLI.

The repository includes a **FastAPI example application** under `app/` that shows how a host can use RailSwitch internally. RailSwitch itself does **not** require FastAPI.

It is an early MVP, not a full blown production-ready payment platform but it stills gives you the chance to build something production ready on top of it .

## Intended architecture

```text
Host application route / domain logic
        ↓
Application service (example: OrderService)
        ↓
  PaymentService
        ↓
PaymentProviderFactory  (dict: Provider -> Provider adapter)
        ↓
  Provider adapter (Paystack / Bachs / Stripe)
        ↓
   Provider API
```

Generated source belongs to the host application. Applications call `PaymentService` directly; they do not make HTTP requests to a payment microservice (but you are liberty to make it work for you as a microservice ).

## CLI usage

Install/run via `uvx` (no fork-local clone needed for users):

```bash
uvx railswitch init
uvx railswitch init --path app/modules/payments
uvx railswitch init --providers paystack
uvx railswitch init --providers paystack stripe
uvx railswitch init --providers paystack --countries GH
uvx railswitch init --countries NG
```

* No `--providers` → all providers (`paystack`, `bach`, `stripe`)
* No `--countries` → all supported countries for the selected providers
* `--countries` without `--providers` infers the provider(s) where unambiguous (e.g. `GH` → `paystack`, `NG` → `bachs`, `CA` → `stripe`). If explicit `--providers` is given, country filtering is applied to those providers and validation fails if a provider does not support a selected country.
* Only selected provider folders/config/env/factory routes are generated. Deduplication preserves input order (`--providers stripe stripe paystack` → `stripe, paystack`).

Source of truth for generation is the provider metadata in `src/railswitch_cli/cli.py` (`ProviderDefinition` / `ProviderCountryDefinition` / `SelectedProviderDefinition`).

## Supported providers and countries

| Provider | Countries | Codes | Default operations via RailSwitch contract |
| --- | --- | --- | --- |
| **Paystack** | Ghana, South Africa | `GH`, `ZA` | Checkout (hosted), transfer disbursement, verification |
| **Bachs** | Nigeria | `NG` | Checkout (hosted), bank-account payout, verification |
| **Stripe** | United States, Canada | `US`, `CA` | Checkout (hosted), verification; **disbursement intentionally unsupported** (`StripeProvider.disburse()` raises `ValueError` - no external account payout) |

Operations on `PaymentService`:

* `collect(CheckoutRequest) -> CheckoutResponse` - hosted checkout
* `disburse(DisbursementRequest) -> DisbursementResponse` - where provider supports the RailSwitch disbursement contract (Paystack/Bachs)
* `verify(VerificationRequest) -> VerificationResponse` - collection or disbursement verification

`PaymentProviderFactory` is generated with routes only for the selected countries, e.g. `--providers paystack --countries GH` generates only `Country.GHANA: Provider.PAYSTACK`.

## Generated structure

`uvx railswitch init --path app/payments` copies shared files and only selected providers, then generates provider-sensitive modules:

```text
app/payments/
├── config.py          # generated: PaymentSettings with only selected country/provider fields
├── contracts.py       # shared dataclass contracts + PaymentProvider ABC
├── dependencies.py    # generated: build_payment_service() / get_payment_service()
├── enums.py           # Country, Currency, CollectionMethod, PaymentProvider, etc.
├── errors.py          # PaymentProviderError + normalized error handling
├── factory.py         # generated: PaymentProviderFactory(providers: dict[Provider, PaymentProvider])
├── service.py         # PaymentService (collect/disburse/verify)
└── providers/
    ├── __init__.py
    ├── paystack/      # only if selected
    ├── bach/          # only if selected
    └── stripe/        # only if selected
```

* `contracts.py`, `service.py`, `enums.py`, `errors.py`, and each `providers/<name>/` are framework-neutral and use relative imports, so a custom `--path` (e.g. `app/modules/payments`) works.
* `config.py`, `dependencies.py`, `factory.py` are **generated** from selected provider/country capabilities.
* The factory constructor is **dict-based**: `PaymentProviderFactory({Provider.PAYSTACK: paystack, ...})`, not `paystack=..., bach=...`.

## Configuration

Settings use `pydantic-settings` with `.env` (`app/payments/config.py`). The CLI updates `.env.example` (never `.env`) with only the variables for selected capabilities.

Examples:

```bash
uvx railswitch init --providers paystack --countries GH
```

generates in `config.py` / `.env.example`:

```env
PAYSTACK_GH_SECRET_KEY=
PAYSTACK_CALLBACK_URL=
```

and does **not** require/generate `PAYSTACK_ZA_SECRET_KEY=`.

```bash
uvx railswitch init --providers stripe
```

```env
STRIPE_SECRET_KEY=
STRIPE_SUCCESS_URL=
STRIPE_CANCEL_URL=
```

Full variable set (when all providers/countries selected):

| Variable | Notes |
| --- | --- |
| `PAYSTACK_GH_SECRET_KEY` | Ghana; per-country credential |
| `PAYSTACK_ZA_SECRET_KEY` | South Africa |
| `PAYSTACK_CALLBACK_URL` | shared Paystack callback |
| `BACH_API_KEY` | Bachs bearer key |
| `BACH_BASE_URL` | defaults to `https://sandbox-api.bachs.io` |
| `STRIPE_SECRET_KEY` | Stripe secret |
| `STRIPE_SUCCESS_URL` / `STRIPE_CANCEL_URL` | Stripe Checkout redirect URLs (required for `collect`) |

`build_payment_service()` validates required credentials via `_paystack_secrets()` / `_bach_api_key()` / `_stripe_secret_key()` helpers generated only for selected providers/countries; missing credentials raise `ValueError`.

## Example integration: FastAPI

The repository's `app/` is **only one** possible host. It demonstrates:

```text
POST /orders/{order_id}/checkout
        ↓
OrderCheckoutRequest (HTTP schema)
        ↓
OrderService
        ↓
CheckoutRequest (internal, reference=order_id, metadata={"order_id": order_id})
        ↓
PaymentService.collect(...)
        ↓
Provider
        ↓
CheckoutResponse (internal)
        ↓
OrderCheckoutResult (app service result)
        ↓
OrderCheckoutResponse (HTTP)
```

### Boundary

* `CheckoutRequest` / `CheckoutResponse` in `app/payments/contracts.py` are **RailSwitch internal** dataclass contracts (6-field `CheckoutResponse` including `provider`, `provider_reference`).
* `OrderCheckoutRequest` (4-field input) / `OrderCheckoutResponse` (4-field output: `order_id`, `reference`, `status`, `checkout_url`) in `app/api/schemas/orders.py` are **host HTTP** Pydantic schemas - `provider`/`provider_reference` are intentionally **not** exposed.
* `OrderCheckoutResult` in `app/orders/service.py` (`@dataclass(slots=True)`) is the host service result (6 fields: `order_id`, `reference`, `provider_reference`, `provider`, `status`, `checkout_url`) mapping from internal `CheckoutResponse`.
* `OrderService` (`app/orders/service.py`) is injected with `PaymentService` via `app/orders/dependencies.py:get_order_service()` which reuses `get_payment_service()` (`@lru_cache`).

### Route

`app/api/routes/order.py`:

```python
@router.post("/{order_id}/checkout", response_model=OrderCheckoutResponse)
async def checkout(order_id: str, body: OrderCheckoutRequest, order_service=Depends(get_order_service)) -> OrderCheckoutResponse: ...
```

`app/main.py` mounts `order_router` (not a generic `/payments/checkout`):

```python
from app.api.routes.order import router as order_router
app.include_router(order_router)
```

`GET /health` remains.

### Example request/response

Request:

```json
POST /orders/ord_123/checkout
{
  "country": "GH",
  "currency": "GHS",
  "amount_minor": 5000,
  "email": "customer@example.com",
  "customer_name": "Customer Example",
  "payment_methods": ["card", "mobile_money"]
}
```

`OrderService` builds:

```python
CheckoutRequest(
    country=Country.GHANA, currency=Currency.GHS, amount_minor=5000,
    email="customer@example.com", customer_name="Customer Example",
    payment_methods=[CollectionMethod.CARD, ...],
    reference="ord_123", metadata={"order_id": "ord_123"}
)
```

Response (`OrderCheckoutResponse` in `app/api/schemas/orders.py` - intentionally 4 fields):

```json
{
  "order_id": "ord_123",
  "reference": "ord_123",
  "status": "pending",
  "checkout_url": "https://checkout.example.test"
}
```

`OrderCheckoutResult` (service layer, `app/orders/service.py`) contains 6 fields including `provider` and `provider_reference`, but `OrderCheckoutResponse` (HTTP) **intentionally drops** `provider` and `provider_reference` - they remain internal to the application service and are not exposed at the HTTP boundary. See `app/api/schemas/orders.py:21` for current 4-field schema.

## Payment references

* `reference` - caller/application correlation ID. For orders: `order_id` is used as `CheckoutRequest.reference` and also stored as `metadata={"order_id": order_id}` so the application owns context. If absent, provider adapters generate `railswitch-<uuid>`.
* `provider_reference` - provider lookup identifier required for later `verify` (e.g. Paystack transfer reference, Bachs `checkout_id`, Stripe `checkout_session_id`). Distinct from `reference` even when they coincide (Paystack).

Verification uses `provider_reference`; without persistence the application must retain the mapping.

## Provider errors

All provider clients normalize failures via `app/payments/errors.py:PaymentProviderError`:

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

* `category`: `validation` (→422), `authentication`, `forbidden`, `not_found` (→404), `conflict` (→409), `insufficient_funds`, `rate_limited` (→429), `processor`, `provider_unavailable` (→502), `unknown`. `http_status_code` property maps category to HTTP.
* `raw_response` is kept internal for logging, never exposed.
* `app/main.py` registers `@app.exception_handler(PaymentProviderError)` returning `public_detail()`.
* `ValueError` from factory/routing or missing config is caught at the route edge as `422` (`raise HTTPException(422, detail=str(error))`).

Provider adapters parse documented error shapes per provider (see `tests/test_provider_errors.py`).

## Development (contributors)

```bash
git clone https://github.com/geraldAp/rails-switch.git
cd rails-switch
uv sync
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

For **users**, prefer the CLI (`uvx railswitch init --providers ... --countries ...`) over cloning. Generated source is owned by the host app.

## Status and limitations

Early open-source, not completely production-ready. Intentionally missing: persistence of transactions/provider metadata, webhooks, reconciliation, retries/circuit breakers, production hardening. Bachs defaults to sandbox (`https://sandbox-api.bachs.io`). DB/Alembic foundation exists but payment layer does not persist transactions. Intended missing areas are not bugs.

Implemented and not missing: Stripe adapter (checkout + verification, disbursement intentionally unsupported), order example (`POST /orders/{order_id}/checkout` is live), Paystack/Bachs/Stripe routing via dict factory.

## Architecture detail

`PaymentProviderFactory` now takes `dict[Provider, PaymentProvider]`:

```python
PaymentProviderFactory({
    Provider.PAYSTACK: paystack,
    Provider.BACH: bach,
    Provider.STRIPE: stripe,
})
```

`_get_default_provider(country)` uses generated `routes: dict[Country, Provider]` built from selected countries, e.g.:

```python
routes = {
            Country.GHANA: Provider.PAYSTACK,
            Country.CANADA: Provider.STRIPE,
}
```

Only selected routes exist; unknown country raises `ValueError("No generated provider is configured for country ...")`, unknown provider raises `ValueError("Provider '...' was not generated")`.

## Adding a provider

Reflects current CLI metadata architecture (`src/railswitch_cli/cli.py`):

1. Implement `providers/<name>/{client.py, mapper.py, provider.py, types.py}` implementing `PaymentProvider` (`collect`/`disburse`/`verify`).
2. Add `ProviderDefinition` with `country_capabilities: tuple[ProviderCountryDefinition(...)]` including `config_fields`, `environment_variables`, `credential_setting` per-country and `shared_*` for provider-level config.
3. Add `shared_config_fields`, `shared_environment_variables`, `dependency_imports`, `service_construction`, `helper_functions`.
4. Update `PROVIDERS` tuple; `PROVIDERS_BY_NAME`, `COUNTRY_CODES` derive automatically.
5. Factory routing, `config.py` comment/fields, `dependencies.py` helpers, and `.env.example` sections are generated - do not hardcode a fixed `__init__(paystack=..., bach=..., stripe=...)`.
6. Add mapper/client/provider/routing tests and verify `CATEGORIES` per provider docs.

Keep provider specifics out of `PaymentService` and keep layers small.

## License

RailSwitch is licensed under the [MIT License](LICENSE).
