from collections.abc import Awaitable
from enum import StrEnum
from typing import cast

import httpx2

from app.payments.enums import PaymentOperation, PaymentProvider


class ProviderErrorCategory(StrEnum):
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    FORBIDDEN = "forbidden"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    INSUFFICIENT_FUNDS = "insufficient_funds"
    RATE_LIMITED = "rate_limited"
    PROCESSOR = "processor"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    UNKNOWN = "unknown"


class PaymentProviderError(Exception):
    """A provider failure expressed in RailSwitch's stable error contract."""

    provider: PaymentProvider
    operation: PaymentOperation
    category: ProviderErrorCategory
    message: str
    provider_code: str | None
    status_code: int | None
    retryable: bool
    raw_response: dict[str, object] | None

    def __init__(
        self,
        *,
        provider: PaymentProvider,
        operation: PaymentOperation,
        category: ProviderErrorCategory,
        message: str,
        provider_code: str | None,
        status_code: int | None,
        retryable: bool,
        raw_response: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.provider = provider
        self.operation = operation
        self.category = category
        self.message = message
        self.provider_code = provider_code
        self.status_code = status_code
        self.retryable = retryable
        self.raw_response = raw_response

    @property
    def http_status_code(self) -> int:
        if self.category is ProviderErrorCategory.VALIDATION:
            return 422
        if self.category is ProviderErrorCategory.NOT_FOUND:
            return 404
        if self.category is ProviderErrorCategory.CONFLICT:
            return 409
        if self.category is ProviderErrorCategory.RATE_LIMITED:
            return 429
        return 502

    def public_detail(self) -> dict[str, object]:
        return {
            "provider": self.provider.value,
            "operation": self.operation.value,
            "category": self.category.value,
            "code": self.provider_code,
            "message": self.message,
            "retryable": self.retryable,
        }


async def send_provider_request(
    request: Awaitable[httpx2.Response],
    *,
    provider: PaymentProvider,
    operation: PaymentOperation,
) -> httpx2.Response:
    """Execute one provider request and normalize transport and HTTP failures."""
    try:
        response = await request
    except httpx2.RequestError as error:
        raise PaymentProviderError(
            provider=provider,
            operation=operation,
            category=ProviderErrorCategory.PROVIDER_UNAVAILABLE,
            message="The payment provider could not be reached.",
            provider_code=None,
            status_code=None,
            retryable=True,
        ) from error

    try:
        _ = response.raise_for_status()
    except httpx2.HTTPStatusError as error:
        raise provider_error_from_response(
            provider=provider,
            operation=operation,
            response=error.response,
        ) from error
    return response


def provider_error_from_response(
    *,
    provider: PaymentProvider,
    operation: PaymentOperation,
    response: httpx2.Response,
) -> PaymentProviderError:
    raw_response = _response_json(response)
    provider_code, message, declared_type = _provider_error_fields(
        provider, raw_response
    )
    category = _category_for(
        status_code=response.status_code,
        provider_code=provider_code,
        declared_type=declared_type,
    )
    return PaymentProviderError(
        provider=provider,
        operation=operation,
        category=category,
        message=message or "The payment provider rejected the request.",
        provider_code=provider_code,
        status_code=response.status_code,
        retryable=category
        in {
            ProviderErrorCategory.RATE_LIMITED,
            ProviderErrorCategory.PROVIDER_UNAVAILABLE,
        },
        raw_response=raw_response or None,
    )


def _response_json(response: httpx2.Response) -> dict[str, object]:
    try:
        payload = cast(object, response.json())
    except ValueError:
        return {}
    if not isinstance(payload, dict):
        return {}
    return {
        str(key): value for key, value in cast(dict[object, object], payload).items()
    }


def _provider_error_fields(
    provider: PaymentProvider, raw_response: dict[str, object]
) -> tuple[str | None, str | None, str | None]:
    if provider is PaymentProvider.STRIPE:
        error = raw_response.get("error")
        if isinstance(error, dict):
            stripe_error = cast(dict[str, object], error)
            return (
                _string(stripe_error.get("code")),
                _string(stripe_error.get("message")),
                _string(stripe_error.get("type")),
            )
    if provider is PaymentProvider.BACH:
        return (
            _string(raw_response.get("error_code")),
            _string(raw_response.get("detail")),
            None,
        )
    return (
        _string(raw_response.get("code")),
        _string(raw_response.get("message")),
        _string(raw_response.get("type")),
    )


def _category_for(
    *,
    status_code: int,
    provider_code: str | None,
    declared_type: str | None,
) -> ProviderErrorCategory:
    code = (provider_code or "").lower()

    match code:
        case "balance_insufficient" | "insufficient_funds" | "insufficient_balance":
            return ProviderErrorCategory.INSUFFICIENT_FUNDS
        case "rate_limit" | "too_many_requests":
            return ProviderErrorCategory.RATE_LIMITED
        case "unauthorized" | "api_key_expired":
            return ProviderErrorCategory.AUTHENTICATION
        case "forbidden" | "payouts_not_allowed":
            return ProviderErrorCategory.FORBIDDEN
        case "resource_missing" | "not_found":
            return ProviderErrorCategory.NOT_FOUND
        case "idempotency_key_in_use" | "conflict":
            return ProviderErrorCategory.CONFLICT
        case _:
            pass

    match status_code:
        case 429:
            return ProviderErrorCategory.RATE_LIMITED
        case status if status >= 500:
            return ProviderErrorCategory.PROVIDER_UNAVAILABLE
        case 401:
            return ProviderErrorCategory.AUTHENTICATION
        case 403:
            return ProviderErrorCategory.FORBIDDEN
        case 404:
            return ProviderErrorCategory.NOT_FOUND
        case 409:
            return ProviderErrorCategory.CONFLICT
        case _:
            pass

    match declared_type:
        case "processor_error":
            return ProviderErrorCategory.PROCESSOR
        case "validation_error":
            return ProviderErrorCategory.VALIDATION
        case _:
            pass

    return (
        ProviderErrorCategory.VALIDATION
        if status_code in {400, 422}
        else ProviderErrorCategory.UNKNOWN
    )


def _string(value: object) -> str | None:
    return value if isinstance(value, str) else None
