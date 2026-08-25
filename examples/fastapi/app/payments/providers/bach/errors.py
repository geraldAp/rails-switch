from ...errors import ProviderErrorCategory, ProviderErrorDetails


def parse_error_details(raw_response: dict[str, object]) -> ProviderErrorDetails:
    code = _string(raw_response.get("error_code"))
    return ProviderErrorDetails(
        code=code,
        message=_string(raw_response.get("detail")),
        category=_category_for_code(code),
    )


def _category_for_code(code: str | None) -> ProviderErrorCategory | None:
    match (code or "").upper():
        case "INSUFFICIENT_BALANCE":
            return ProviderErrorCategory.INSUFFICIENT_FUNDS
        case "TOO_MANY_REQUESTS":
            return ProviderErrorCategory.RATE_LIMITED
        case "UNAUTHORIZED":
            return ProviderErrorCategory.AUTHENTICATION
        case "FORBIDDEN":
            return ProviderErrorCategory.FORBIDDEN
        case "NOT_FOUND" | "DESTINATION_NOT_FOUND" | "PAYOUT_DESTINATION_NOT_FOUND":
            return ProviderErrorCategory.NOT_FOUND
        case "IDEMPOTENCY_IN_PROGRESS" | "CONFLICT" | "CHECKOUT_PRICE_CHANGED":
            return ProviderErrorCategory.CONFLICT
        case _:
            return None


def _string(value: object) -> str | None:
    return value if isinstance(value, str) else None
