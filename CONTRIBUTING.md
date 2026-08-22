# Contributing to RailSwitch

RailSwitch accepts provider adapters only when their tests prove the provider's
real API contract. Tests should describe an observable provider rule, not just
exercise a shared base class or assert that a method returns a value.

## Adding a provider

Keep the adapter split into `client.py`, `mapper.py`, `provider.py`, and
`types.py`. The client owns HTTP details, the mapper owns translation, and the
provider orchestrates the shared RailSwitch contracts. Do not put provider
credentials or endpoint rules in `PaymentService` or the factory.

## Required tests for a provider adapter

Add focused tests for every operation the provider supports.

| Layer | What a test must prove |
| --- | --- |
| Mapper | Exact provider request payload, amount/currency conversion, supported methods, rejection of unsupported methods, normalized status, `metadata`, and `raw_response`. |
| Client | Exact HTTP method, URL, authentication headers, request payload, and the typed provider response returned from the HTTP boundary. |
| Provider | The provider calls the correct client operation, generates a reference before an initiation call when needed, and returns the normalized response. |
| Verification | `PaymentOperation` selects the correct provider endpoint and `provider_reference` is the exact lookup value passed to that endpoint. |
| Factory | Country routing or an explicit provider override, when the provider changes routing. |
| Error handling | Provider-specific documented error payloads map to `PaymentProviderError`; cover validation, authentication, not found, conflict, rate limit, provider `5xx`, and a network failure. |

For an initiation response, test both identifiers deliberately:

```text
reference          = caller-supplied or RailSwitch-generated application ID
provider_reference = the value required by the provider lookup endpoint
```

Include one test where the values legitimately match and one where they differ
when the provider supports both cases. Do not use an arbitrary provider `id` as
`provider_reference`: consult the provider's retrieval or verification endpoint
and test the exact required value.

Use a small recording fake client in provider tests. It should capture the
endpoint argument or payload that matters to the assertion. Avoid generic stub
tests that merely return a fixed response without proving a provider-specific
rule.

For error tests, use the provider's official API error documentation as the
source of the fixture shape and error codes. Do not copy one provider's error
format into another adapter.

## Running checks

Run these before opening a pull request:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uvx basedpyright app/payments tests
```

Do not use live credentials or call real provider APIs in the test suite.
