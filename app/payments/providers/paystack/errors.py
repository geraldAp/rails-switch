from app.payments.errors import ProviderErrorCategory, ProviderErrorDetails


def parse_error_details(raw_response: dict[str, object]) -> ProviderErrorDetails:
    code = _string(raw_response.get("code"))
    declared_type = _string(raw_response.get("type"))
    return ProviderErrorDetails(
        code=code,
        message=_string(raw_response.get("message")),
        category=_category_for(code, declared_type),
    )


def _category_for(
    code: str | None, declared_type: str | None
) -> ProviderErrorCategory | None:
    match (code or "").lower():
        case "balance_insufficient" | "insufficient_funds":
            return ProviderErrorCategory.INSUFFICIENT_FUNDS
        case "rate_limit" | "too_many_requests":
            return ProviderErrorCategory.RATE_LIMITED
        case "idempotency_key_in_use" | "conflict":
            return ProviderErrorCategory.CONFLICT
        case _:
            pass

    match declared_type:
        case "processor_error":
            return ProviderErrorCategory.PROCESSOR
        case "validation_error":
            return ProviderErrorCategory.VALIDATION
        case _:
            return None


def _string(value: object) -> str | None:
    return value if isinstance(value, str) else None
