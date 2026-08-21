from enum import StrEnum
from typing import NotRequired, TypedDict


# ── ENUMS ──────────────────────────────────────────────────────────
class BachPaymentMethod(StrEnum):
    CARD = "card"
    BANK_TRANSFER = "bank_transfer"
    MOBILE_MONEY = "mobile_money"


# ── COLLECTIONS (CHECKOUT) ─────────────────────────────────────────
class BachPricing(TypedDict):
    currency: str
    amount: str


class BachCustomer(TypedDict):
    email: str


class BachCheckoutRequest(TypedDict):
    pricing: BachPricing
    customer: BachCustomer
    reference: str
    payment_methods: NotRequired[list[BachPaymentMethod]]
    metadata: NotRequired[dict[str, str]]


class BachCheckoutResponse(TypedDict):
    checkout_id: str
    reference: str
    status: str
    amount: str
    currency: str
    checkout_url: str


# ── TRANSACTION FINDING (VERIFICATION) ─────────────────────────────
class BachCheckoutDetails(TypedDict):
    checkout_id: str
    status: str
    amount: str
    currency: str
    payment_status: NotRequired[str | None]


# ── DISBURSEMENTS (TRANSFERS) ──────────────────────────────────────
class BachPayoutDestinationRequest(TypedDict):
    currency: str
    account_number: str
    bank_code: str
    name: str
    metadata: NotRequired[dict[str, str]]


class BachPayoutDestinationResponse(TypedDict):
    id: str
    status: str
    is_usable: bool


class BachPayoutRequest(TypedDict):
    destination: str
    amount: str
    reference: str
    metadata: NotRequired[dict[str, str]]


class BachPayoutResponse(TypedDict):
    id: str
    status: str
    amount: str
    currency: str
    reference: str | None
    source_currency: NotRequired[str | None]
    fee: NotRequired[str | None]
    total_debited: NotRequired[str | None]
    destination: NotRequired[str | None]
    failure_reason: NotRequired[str | None]
    created_at: NotRequired[str | None]
    completed_at: NotRequired[str | None]


class BachPayoutDetails(BachPayoutResponse):
    """The Get Payout response has the same shape as payout creation."""
