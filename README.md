# RailSwitch

RailSwitch is a small Python/FastAPI  project that explores payment
orchestration. Applications use one normalized payment interface while the
project translates that interface to the APIs of individual payment providers.

It is an early MVP, not a production-ready payment platform.

## Why RailSwitch exists

Payment providers differ in request payloads, authentication, payment-method
names, amount formats, transaction states, and payout flows. For example,
Paystack accepts amounts in minor units, while Bachs accepts decimal strings;
Paystack transfers first create a recipient, while Bachs payouts first create a
destination that may need approval.

RailSwitch keeps those details in provider adapters and gives the rest of an
application shared contracts such as `CheckoutRequest`, `DisbursementRequest`,
and `VerificationRequest`.

## Current capabilities

Implemented in the payment layer:

- Hosted checkout collection.
- Account disbursement.
- Transaction verification.
- Paystack and Bachs provider adapters.
- Normalized `pending`, `success`, and `failed` statuses.

Intentionally not implemented:

- Refunds, webhooks, reconciliation, retries, circuit breakers, and smart
  routing.
- Transaction or beneficiary persistence.
- Additional providers such as Stripe.
- HTTP routes for disbursement and verification.

The FastAPI application currently registers only `GET /health`. A checkout
route handler and its Pydantic request schema exist in `app/api`, but the router
is not yet included by `app/main.py`; consequently, `/payments/checkout` is not
currently a live endpoint.

## Supported providers and countries

`PaymentProviderFactory` supplies the following default routing:

| Country | Default provider | Adapter support |
| --- | --- | --- |
| Ghana (`GH`) | Paystack | Checkout, transfer disbursement, verification |
| Nigeria (`NG`) | Bachs | Checkout, bank-account payout, verification |
| South Africa (`ZA`) | Paystack | Checkout, transfer disbursement, verification |

An explicit provider can be supplied for verification. The factory chooses the
provider implementation only; provider configuration stays in the provider's
client. In particular, the one Paystack client resolves separate Ghana and
South Africa credentials from the request country.

## Architecture

```text
HTTP route / internal caller
          |
          v
    PaymentService
          |
          v
PaymentProviderFactory
          |
          v
 PaystackProvider or BachProvider
          |
          v
        Mapper
          |
          v
        Client
          |
          v
 External provider API
```

| Layer | Responsibility |
| --- | --- |
| API schemas and routes | Validate and translate HTTP input at the application edge. The current checkout schema is `CheckoutRequestBody`. |
| `PaymentService` | Thin common interface: select a provider and call `collect`, `disburse`, or `verify`. |
| `PaymentProviderFactory` | Choose the default adapter from country, or use the explicit provider supplied for verification. |
| Provider | Implement the shared `PaymentProvider` contract and coordinate a provider operation. |
| Mapper | Translate RailSwitch contracts to/from provider-specific payloads and statuses. |
| Client | Own base URL, bearer authentication, HTTPX2 requests, and response parsing. |
| Provider types | Define provider API shapes with `TypedDict`/enums. |
| Shared contracts and enums | Define the provider-neutral dataclass requests/responses and supported RailSwitch values. |
| `dependencies.py` | Manual composition root for clients, providers, factory, and `PaymentService`. |

### HTTP models vs. internal contracts

Pydantic models at the HTTP edge are not the same thing as RailSwitch's internal
dataclass contracts. For example, `CheckoutRequestBody` uses `EmailStr` to
validate a request body, then the route creates a `CheckoutRequest` for the
payment layer. This keeps FastAPI/Pydantic concerns out of provider adapters
and lets internal callers use `PaymentService` directly rather than making HTTP
requests back into the same application.

## Dependency wiring

`build_payment_service()` in `app/payments/dependencies.py` assembles the
object graph:

```text
PaystackClient + BachClient
             |
             v
PaystackProvider + BachProvider
             |
             v
    PaymentProviderFactory
             |
             v
       PaymentService
```

Constructing or injecting `PaymentService` does not make a payment. A payment
operation happens only when a caller awaits `collect()`, `disburse()`, or
`verify()`. `get_payment_service()` wraps construction in `@lru_cache` so a
FastAPI dependency can reuse the assembled service; the cache is not itself a
dependency-injection framework.

## Repository structure

```text
app/
├── api/
│   ├── routes/payment.py       # Checkout handler (not yet mounted)
│   └── schemas/payments.py     # Pydantic HTTP schema
├── core/config.py              # Pydantic settings
├── db/                         # SQLAlchemy/Alembic foundation
├── main.py                     # FastAPI application and health route
└── payments/
    ├── contracts.py            # Provider-neutral dataclass contracts and ABC
    ├── enums.py                # RailSwitch status, country, currency, methods
    ├── factory.py              # Default provider selection
    ├── service.py              # Thin orchestration layer
    ├── dependencies.py         # Manual composition root
    └── providers/
        ├── paystack/           # Paystack types, mapper, client, provider
        └── bach/               # Bachs types, mapper, client, provider
tests/
├── test_payment_service.py     # Factory and service orchestration coverage
├── test_paystack.py            # Paystack mapping, client, and provider coverage
└── test_bach.py                # Bachs mapping, client, provider, wiring tests
```

## Payment flow examples

### Checkout flow

The checkout handler is written to perform this flow once its router is mounted:

```text
POST /payments/checkout
  -> FastAPI validates CheckoutRequestBody
  -> route builds CheckoutRequest
  -> PaymentService.collect()
  -> factory selects the default provider for country
  -> provider mapper builds the provider payload
  -> provider client calls the external API
  -> mapper normalizes the response to CheckoutResponse
```

Disbursement and verification are implemented on `PaymentService` and both
providers, but they do not currently have HTTP handlers. Internal application
code can call the service directly.

### Provider differences that RailSwitch absorbs

- **Paystack checkout and transfer amounts** remain minor-unit values. Its
  client selects the Ghana or South Africa bearer key from `request.country`.
- **Paystack disbursement** creates a transfer recipient, generates one
  `railswitch-<uuid>` application reference when the caller did not supply one,
  then initiates the transfer. Paystack uses that value as its transfer lookup
  reference, so `reference` and `provider_reference` can legitimately match.
- **Bachs checkout and payout amounts** are mapped from integer minor units to
  two-decimal `Decimal` strings (for example, `5000` NGN becomes `"50.00"`).
- **Bachs checkout verification** uses the Bachs `checkout_id` as
  `provider_reference`, because Bachs retrieves checkout sessions by that ID.
- **Bachs payout destinations** must report `is_usable: true` before a payout
  is created. A pending-review destination raises a clear error instead of
  pretending a payout exists.

## Getting started

Prerequisites:

- Python 3.13 or newer (the project declares `requires-python = ">=3.13"`).
- [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/geraldAp/rails-switch.git
cd rails-switch
uv sync
```

The clone URL above is the repository's configured `origin` remote. If you are
working from a fork, use your fork's URL instead.

## Environment variables

Settings load from `.env`; `.gitignore` excludes that file. Never commit real
keys.

Create a local `.env` when you need to construct and use the payment service:

```env
PAYSTACK_GH_SECRET_KEY=
PAYSTACK_ZA_SECRET_KEY=
PAYSTACK_CALLBACK_URL=
BACH_API_KEY=
```

| Variable | Required for payment flows | Notes |
| --- | --- | --- |
| `PAYSTACK_GH_SECRET_KEY` | Yes | Paystack credentials for Ghana. |
| `PAYSTACK_ZA_SECRET_KEY` | Yes | Paystack credentials for South Africa. |
| `PAYSTACK_CALLBACK_URL` | Yes in practice for Paystack checkout | Its code default is an empty string, but a real checkout should use a valid callback URL. |
| `BACH_API_KEY` | Yes | Bachs bearer key. |
| `BACH_BASE_URL` | No | Defaults to `https://sandbox-api.bachs.io`. Keep sandbox keys with the sandbox URL. |
| `APP_NAME` | No | Defaults to `RailSwitch`. |
| `ENVIRONMENT` | No | Defaults to `development`. |
| `DATABASE_URL` | No | Defaults to `sqlite+aiosqlite:///./railswitch.db`. |

`build_payment_service()` fails clearly if either Paystack secret or the Bachs
API key is missing. The health endpoint alone does not construct the payment
service.

## Running the API

```bash
uv run uvicorn app.main:app --reload
```

Then visit:

- Health: <http://127.0.0.1:8000/health>
- Swagger UI: <http://127.0.0.1:8000/docs>
- OpenAPI JSON: <http://127.0.0.1:8000/openapi.json>

At present, the registered application endpoint is:

```http
GET /health
```

Response:

```json
{"status":"ok"}
```

The checkout request model prepared for the unmounted route accepts this body:

```json
{
  "country": "GH",
  "amount_minor": 5000,
  "currency": "GHS",
  "email": "customer@example.com",
  "payment_methods": ["card", "mobile_money"]
}
```

`amount_minor: 5000` represents GHS 50.00. When the route is mounted and the
provider call succeeds, the normalized checkout result keeps application and
provider identifiers separate:

```json
{
  "reference": "PAY-456",
  "provider_reference": "provider-or-checkout-reference",
  "provider": "paystack",
  "status": "pending",
  "checkout_url": "https://provider-hosted-checkout.example",
  "payment_methods": ["card", "mobile_money"]
}
```

`reference` is the caller's application correlation ID (supplied or generated
by RailSwitch before the provider call). `provider_reference` is the provider
identifier required for later verification. These may have the same value for
Paystack, but are intentionally separate concepts. Verification accepts a
`provider_reference`; without persistence, RailSwitch cannot recover the
caller reference during verification. A future transaction record will retain
both values together with metadata and the raw provider response.

## Running tests

```bash
uv run pytest
```

The suite covers factory routing, Paystack country-aware credentials and
transfers, Bachs amount/status mappings, Bachs checkout and payout behaviour,
the destination-approval guard, client idempotency headers, and composition.

Useful additional checks:

```bash
uv run ruff check .
uv run ruff format --check .
```

## Adding a provider

Follow the existing compact adapter shape:

```text
providers/
└── new_provider/
    ├── client.py
    ├── mapper.py
    ├── provider.py
    └── types.py
```

1. Implement `PaymentProvider` in `provider.py`.
2. Define only the provider request/response shapes needed in `types.py`.
3. Put HTTPX2 endpoints and authentication in `client.py`.
4. Translate RailSwitch contracts and provider shapes in `mapper.py`.
5. Add the provider to `PaymentProviderFactory` and choose its default country
   routing where appropriate.
6. Add constructor-injected configuration in `core/config.py` and compose it
   in `dependencies.py`.
7. Add focused mapper, client, provider, and routing tests.

Keep provider credentials and API semantics out of `PaymentService` and the
factory. Avoid adding extra architectural layers unless the project genuinely
needs them.

## Design principles

- Keep orchestration thin.
- Use normalized internal contracts.
- Keep provider-specific details inside provider modules.
- Let internal services call `PaymentService` directly.
- Keep configuration separate from provider selection.
- Prefer small, readable code over premature complexity.

## Status and limitations

RailSwitch is evolving as a learning/open-source project. Important current
limitations include no payment persistence, no mounted payment router, no HTTP
disbursement or verification routes, no webhook handling, and no production
readiness claim. Bachs defaults to its sandbox base URL. The database and
Alembic foundation exist, but the payment layer does not persist transactions
or payout destinations.

## Roadmap

- Mount and complete the existing payment HTTP surface.
- Persist transaction/provider metadata so verification does not require a
  caller to resupply it.
- Add more countries and provider adapters while retaining the shared contract.

## Contributing

Contributions are welcome. Fork the repository, create a focused branch, add
or update tests, and open a pull request. Provider contributions should follow
the existing client/mapper/provider/types arrangement and keep the shared
service and factory small.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the required provider test cases and
contribution workflow.

## License

RailSwitch is licensed under the [MIT License](LICENSE).
