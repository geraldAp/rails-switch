from typing import NotRequired, TypedDict


class BachPricing(TypedDict):
    currency: str
    amount: str


class BachCustomer(TypedDict):
    email: str


class BachCheckoutRequest(TypedDict):
    pricing: BachPricing
    customer: BachCustomer
    reference: str
    payment_methods: NotRequired[list[str]]


class BachCheckoutResponse(TypedDict):
    checkout_id: str
    reference: str
    status: str
    amount: str
    currency: str
    checkout_url: str


class BachCheckoutDetails(TypedDict):
    checkout_id: str
    status: str
    amount: str
    currency: str
    payment_status: NotRequired[str | None]


class BachPayoutDestinationRequest(TypedDict):
    currency: str
    account_number: str
    bank_code: str
    name: str


class BachPayoutDestinationResponse(TypedDict):
    id: str
    status: str
    is_usable: bool


class BachPayoutRequest(TypedDict):
    destination: str
    amount: str
    reference: str


class BachPayoutResponse(TypedDict):
    status: str
    reference: str
