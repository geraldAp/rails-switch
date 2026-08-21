from typing import NotRequired, TypedDict


class StripeCheckoutRequest(TypedDict):
    mode: str
    customer_email: str
    success_url: str
    cancel_url: str
    payment_method_types: NotRequired[list[str]]
    line_items: list[dict[str, object]]


class StripeCheckoutSession(TypedDict):
    id: str
    url: str
    payment_status: str
    amount_total: int | None
    currency: str | None
    payment_intent: str | None


class StripePaymentIntent(TypedDict):
    status: str
    amount: int
    currency: str


class StripePayout(TypedDict):
    id: str
    status: str
    amount: int
    currency: str
