import asyncio

import httpx2
import pytest

from app.payments.enums import PaymentOperation, PaymentProvider
from app.payments.errors import (
    PaymentProviderError,
    ProviderErrorCategory,
    provider_error_from_response,
    send_provider_request,
)


@pytest.mark.parametrize(
    ("provider", "payload", "expected_code", "expected_category"),
    [
        (
            PaymentProvider.STRIPE,
            {
                "error": {
                    "code": "parameter_invalid_empty",
                    "message": "You passed an empty string for 'success_url'.",
                    "type": "invalid_request_error",
                }
            },
            "parameter_invalid_empty",
            ProviderErrorCategory.VALIDATION,
        ),
        (
            PaymentProvider.PAYSTACK,
            {
                "status": False,
                "message": "Email Address is required",
                "type": "validation_error",
                "code": "missing_params",
            },
            "missing_params",
            ProviderErrorCategory.VALIDATION,
        ),
        (
            PaymentProvider.BACH,
            {
                "detail": "base_currency 'NGN' is not held by this organization.",
                "error_code": "BASE_CURRENCY_NOT_HELD_BY_ORG",
            },
            "BASE_CURRENCY_NOT_HELD_BY_ORG",
            ProviderErrorCategory.VALIDATION,
        ),
    ],
)
def test_provider_error_parses_each_documented_error_shape(
    provider: PaymentProvider,
    payload: dict[str, object],
    expected_code: str,
    expected_category: ProviderErrorCategory,
) -> None:
    error = provider_error_from_response(
        provider=provider,
        operation=PaymentOperation.COLLECTION,
        response=httpx2.Response(400, json=payload),
    )

    assert error.provider is provider
    assert error.provider_code == expected_code
    assert error.category is expected_category
    assert error.raw_response == payload


@pytest.mark.parametrize(
    ("status_code", "code", "expected_category", "retryable"),
    [
        (401, "UNAUTHORIZED", ProviderErrorCategory.AUTHENTICATION, False),
        (403, "FORBIDDEN", ProviderErrorCategory.FORBIDDEN, False),
        (404, "NOT_FOUND", ProviderErrorCategory.NOT_FOUND, False),
        (409, "CONFLICT", ProviderErrorCategory.CONFLICT, False),
        (429, "TOO_MANY_REQUESTS", ProviderErrorCategory.RATE_LIMITED, True),
        (
            500,
            "INTERNAL_SERVER_ERROR",
            ProviderErrorCategory.PROVIDER_UNAVAILABLE,
            True,
        ),
    ],
)
def test_bachs_documented_http_error_scenarios_are_normalized(
    status_code: int,
    code: str,
    expected_category: ProviderErrorCategory,
    retryable: bool,
) -> None:
    error = provider_error_from_response(
        provider=PaymentProvider.BACH,
        operation=PaymentOperation.DISBURSEMENT,
        response=httpx2.Response(
            status_code,
            json={"detail": "Provider failure", "error_code": code},
        ),
    )

    assert error.category is expected_category
    assert error.retryable is retryable


def test_stripe_insufficient_balance_is_normalized() -> None:
    error = provider_error_from_response(
        provider=PaymentProvider.STRIPE,
        operation=PaymentOperation.DISBURSEMENT,
        response=httpx2.Response(
            400,
            json={
                "error": {
                    "code": "balance_insufficient",
                    "message": "Insufficient funds.",
                    "type": "invalid_request_error",
                }
            },
        ),
    )

    assert error.category is ProviderErrorCategory.INSUFFICIENT_FUNDS
    assert error.http_status_code == 502


def test_paystack_processor_error_is_normalized() -> None:
    error = provider_error_from_response(
        provider=PaymentProvider.PAYSTACK,
        operation=PaymentOperation.COLLECTION,
        response=httpx2.Response(
            400,
            json={
                "status": False,
                "message": "Card declined",
                "type": "processor_error",
                "code": "card_declined",
            },
        ),
    )

    assert error.category is ProviderErrorCategory.PROCESSOR


def test_network_error_is_retryable_and_has_no_provider_payload() -> None:
    async def unavailable() -> httpx2.Response:
        raise httpx2.ConnectError("Connection refused")

    with pytest.raises(PaymentProviderError) as raised:
        _ = asyncio.run(
            send_provider_request(
                unavailable(),
                provider=PaymentProvider.PAYSTACK,
                operation=PaymentOperation.COLLECTION,
            )
        )

    assert raised.value.category is ProviderErrorCategory.PROVIDER_UNAVAILABLE
    assert raised.value.retryable
    assert raised.value.raw_response is None
