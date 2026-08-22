from typing import cast

from app.payments.errors import ProviderErrorCategory, ProviderErrorDetails


def parse_error_details(raw_response: dict[str, object]) -> ProviderErrorDetails:
    error = raw_response.get("error")
    if not isinstance(error, dict):
        return ProviderErrorDetails()

    stripe_error = cast(dict[str, object], error)
    code = _string(stripe_error.get("code"))
    return ProviderErrorDetails(
        code=code,
        message=_string(stripe_error.get("message")),
        category=_category_for_code(code),
    )


def _category_for_code(code: str | None) -> ProviderErrorCategory | None:
    match (code or "").lower():
        case "balance_insufficient" | "insufficient_funds":
            return ProviderErrorCategory.INSUFFICIENT_FUNDS
        case "rate_limit":
            return ProviderErrorCategory.RATE_LIMITED
        case "api_key_expired" | "secret_key_required":
            return ProviderErrorCategory.AUTHENTICATION
        case "payouts_not_allowed" | "capability_not_active":
            return ProviderErrorCategory.FORBIDDEN
        case "resource_missing":
            return ProviderErrorCategory.NOT_FOUND
        case "idempotency_key_in_use":
            return ProviderErrorCategory.CONFLICT
        case _:
            return None


def _string(value: object) -> str | None:
    return value if isinstance(value, str) else None
