from collections.abc import Awaitable, Callable
from dataclasses import dataclass
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


@dataclass(frozen=True, slots=True)
class ProviderErrorDetails:
    """Provider-specific error fields extracted by a provider adapter."""

    code: str | None = None
    message: str | None = None
    category: ProviderErrorCategory | None = None


ProviderErrorParser = Callable[[dict[str, object]], ProviderErrorDetails]


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
    error_parser: ProviderErrorParser,
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
            error_parser=error_parser,
        ) from error
    return response


def provider_error_from_response(
    *,
    provider: PaymentProvider,
    operation: PaymentOperation,
    response: httpx2.Response,
    error_parser: ProviderErrorParser,
) -> PaymentProviderError:
    raw_response = _response_json(response)
    details = error_parser(raw_response)
    category = details.category or _category_from_http_status(response.status_code)
    return PaymentProviderError(
        provider=provider,
        operation=operation,
        category=category,
        message=details.message or "The payment provider rejected the request.",
        provider_code=details.code,
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


def _category_from_http_status(status_code: int) -> ProviderErrorCategory:
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
            return (
                ProviderErrorCategory.VALIDATION
                if status_code in {400, 422}
                else ProviderErrorCategory.UNKNOWN
            )
