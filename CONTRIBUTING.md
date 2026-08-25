# Contributing to RailSwitch

RailSwitch is a framework-agnostic Python payment orchestration and scaffolding
project. Keep contributions small, provider-neutral where possible, and backed
by focused tests.

## Development setup

RailSwitch requires Python 3.13 or newer and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/geraldAp/rails-switch.git
cd rails-switch
uv sync
```

Run all checks before opening a pull request:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

The FastAPI app in this repository is an example integration, not a RailSwitch
requirement.

## Repository layout

- `src/railswitch_cli/` is the published CLI and scaffolder.
- `src/railswitch_cli/templates/` contains the static source copied into generated payment modules.
- `examples/fastapi/` contains the reference FastAPI host application and its Alembic setup.
- `tests/` covers the CLI, provider contracts, and reference-app integration.

## Architecture

```text
PaymentService
      ↓
PaymentProviderFactory
      ↓
Provider → Mapper → Client → Provider API
```

- `contracts.py` defines normalized RailSwitch request and response contracts.
- `service.py` is thin orchestration: it delegates provider selection to the
  factory and operations to the selected provider.
- `factory.py` validates and selects provider-country capabilities.
- `provider.py` implements `PaymentProvider`.
- `mapper.py` translates between RailSwitch contracts and provider payloads.
- `client.py` owns provider HTTP/API behavior.
- `types.py` holds provider-specific API shapes.
- `errors.py` normalizes provider failures.

Keep provider-specific credentials, endpoints, payloads, and compatibility
rules out of `PaymentService`.

## Provider-country routing

Routing is modeled as:

```text
Country → set[PaymentProvider]
```

When one provider is configured for a country, collection or disbursement
selects it if `provider` is omitted. When multiple providers are configured,
the caller must choose one explicitly. An incompatible provider-country pair is
rejected. RailSwitch v0.1 has no default-provider priority.

Preserve this model when adding providers or countries. Do not reintroduce a
fixed provider constructor or a single default-provider map.

## Adding a provider

A provider normally includes:

```text
providers/<provider>/
├── __init__.py
├── client.py
├── errors.py
├── mapper.py
├── provider.py
└── types.py
```

Checklist:

1. Add the `PaymentProvider` enum entry when needed.
2. Implement the `PaymentProvider` contract.
3. Define provider API request and response types.
4. Implement client authentication and endpoints.
5. Add request/response mapping and provider error normalization.
6. Add `ProviderDefinition` metadata in `src/railswitch_cli/cli.py`.
7. Add its `ProviderCountryDefinition` capabilities and required shared or
   country-specific environment/config metadata.
8. Add focused provider, routing, and CLI tests.
9. Verify generated scaffolds include the provider only when selected.

Do not manually add a fixed provider constructor for a new adapter.

## Adding a country to a provider

Country support is metadata-driven. It normally starts by adding a
`ProviderCountryDefinition` to the provider's `country_capabilities`:

```text
ProviderDefinition
└── country_capabilities += ProviderCountryDefinition(...)
```

A capability can define its country code, `Country` enum name, display name,
country-specific environment variables, config fields, and credential setting.
Update the `Country` enum when necessary; update currency/method enums or
provider client/mapper behavior only when the provider API genuinely requires
it. Add tests for routing and credentials.

Do not create provider-country combination templates.

## Provider conformance requirements

Every provider must be added to the shared conformance matrix in
`tests/test_provider_conformance.py`. The matrix verifies the common
RailSwitch contract: collection, verification, normalized references and
statuses, disbursement or an explicit unsupported result, and unsupported
methods or capabilities where relevant.

Shared conformance tests **and** provider-specific tests are required.
Provider-specific suites should continue to cover unique API payloads,
authentication, error shapes, country/provider capability routing, and any
provider-specific idempotency behavior. Normalized provider error coverage must
exist for every provider, whether in the conformance suite or the dedicated
error tests.

## Tests

Provider work should cover applicable request mapping, response/status and
amount normalization, authentication/header behavior, collection,
disbursement, verification, documented provider errors, network failures,
country-specific credentials/routing, and idempotency behavior where present.
Use mocks, spies, or fakes—never real provider APIs or credentials.

Scaffolding changes should verify selected provider directories and countries;
generated `config.py`, `dependencies.py`, `factory.py`, and `.env.example`;
omitted imports; generated code compilation/imports; and provider-country
routing. `config.py`, `dependencies.py`, and `factory.py` are generated
dynamically by the CLI and must not be reintroduced as static templates.

## Contracts and errors

Changes to `CheckoutRequest`, `CheckoutResponse`, `DisbursementRequest`,
`DisbursementResponse`, `VerificationRequest`, `VerificationResponse`, or
`PaymentProvider` affect every adapter. Keep changes deliberate,
backwards-conscious, normalized, and tested across affected providers. Do not
add provider-specific fields to shared contracts unless they express a genuine
RailSwitch concept.

Provider clients should normalize failures into `PaymentProviderError` and map
provider codes/statuses to `ProviderErrorCategory`. Do not expose raw provider
responses publicly; `raw_response` may contain sensitive payment or customer
data.

## Pull requests and security

Use descriptive branch names, clear commits, and focused pull requests. Include
what changed, why, affected provider/country, tests added or updated, relevant
official provider documentation, and known limitations. Avoid unrelated
refactors.

Never commit API keys or secrets, add them to fixtures, or expose them in
examples. Keep `.env` uncommitted and sanitize provider payloads used in tests
and documentation.
