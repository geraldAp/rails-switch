from enum import StrEnum
from typing import NotRequired, TypedDict


# ── ENUMS ──────────────────────────────────────────────────────────
class PaystackChannel(StrEnum):
    CARD = "card"
    BANK = "bank"
    APPLE_PAY = "apple_pay"
    USSD = "ussd"
    QR = "qr"
    MOBILE_MONEY = "mobile_money"
    BANK_TRANSFER = "bank_transfer"
    EFT = "eft"
    CAPITEC_PAY = "capitec_pay"
    PAYATTITUDE = "payattitude"


class PaystackRecipientType(StrEnum):
    NUBAN = "nuban"
    GHIPSS = "ghipss"
    MOBILE_MONEY = "mobile_money"
    BASA = "basa"


class PaystackBearer(StrEnum):
    ACCOUNT = "account"
    SUBACCOUNT = "subaccount"


# ── COLLECTIONS (CHECKOUT) ─────────────────────────────────────────
class PaystackCheckoutRequest(TypedDict):
    amount: str
    email: str
    callback_url: str

    channels: NotRequired[list[PaystackChannel]]
    currency: NotRequired[str]
    reference: NotRequired[str]
    bearer: NotRequired[PaystackBearer]
    metadata: NotRequired[str]


class PaystackCheckoutData(TypedDict):
    authorization_url: str
    access_code: str
    reference: str


class PaystackCheckoutResponse(TypedDict):
    status: bool
    message: str
    data: PaystackCheckoutData


# ── TRANSACTION FINDING (VERIFICATION) ─────────────────────────────
class PaystackTransactionHistory(TypedDict):
    type: str
    message: str
    time: int


class PaystackTransactionLog(TypedDict):
    start_time: int
    time_spent: int
    attempts: int
    errors: int
    success: bool
    mobile: bool
    input: list[object]
    history: list[PaystackTransactionHistory]


class PaystackAuthorization(TypedDict):
    authorization_code: str
    bin: str
    last4: str
    exp_month: str
    exp_year: str
    channel: str
    card_type: str
    bank: str
    country_code: str
    brand: str
    reusable: bool
    signature: str
    account_name: str | None


class PaystackCustomer(TypedDict):
    id: int
    first_name: str | None
    last_name: str | None
    email: str
    customer_code: str
    phone: str | None
    metadata: object | None
    risk_action: str
    international_format_phone: str | None


class PaystackVerificationData(TypedDict):
    id: int
    domain: str
    status: str
    reference: str
    receipt_number: str | None
    amount: int
    message: str | None
    gateway_response: str
    paid_at: str | None
    created_at: str
    channel: str
    currency: str
    ip_address: str | None

    metadata: str | dict[str, object] | None
    log: PaystackTransactionLog | None

    fees: int | None
    fees_split: object | None

    authorization: PaystackAuthorization
    customer: PaystackCustomer

    plan: object | None
    split: dict[str, object]
    order_id: int | str | None

    paidAt: str | None
    createdAt: str

    requested_amount: int

    pos_transaction_data: object | None
    source: object | None
    fees_breakdown: object | None
    connect: object | None

    transaction_date: str

    plan_object: dict[str, object]
    subaccount: dict[str, object]


class PaystackVerificationResponse(TypedDict):
    status: bool
    message: str
    data: PaystackVerificationData


# ── DISBURSEMENTS (TRANSFERS) ──────────────────────────────────────
class PaystackTransferRecipientRequest(TypedDict):
    type: PaystackRecipientType
    name: str
    account_number: str
    bank_code: str

    currency: NotRequired[str]
    description: NotRequired[str]
    metadata: NotRequired[dict[str, object]]


class PaystackRecipientDetails(TypedDict):
    authorization_code: str | None
    account_number: str | None
    account_name: str | None
    bank_code: str
    bank_name: str


class PaystackTransferRecipientData(TypedDict):
    active: bool
    createdAt: str
    currency: str
    domain: str
    id: int
    integration: int
    name: str
    recipient_code: str
    type: str
    updatedAt: str
    is_deleted: bool
    details: PaystackRecipientDetails


class PaystackTransferRecipientResponse(TypedDict):
    status: bool
    message: str
    data: PaystackTransferRecipientData


class PaystackTransferRequest(TypedDict):
    source: str
    amount: int
    recipient: str
    reference: str

    reason: NotRequired[str]
    currency: NotRequired[str]


class PaystackTransferData(TypedDict):
    domain: str
    amount: int
    currency: str
    reference: str
    source: str
    source_details: object | None
    reason: str | None
    status: str
    failures: object | None
    transfer_code: str
    titan_code: str | None
    transferred_at: str | None
    id: int
    integration: int
    recipient: int
    createdAt: str
    updatedAt: str


class PaystackTransferResponse(TypedDict):
    status: bool
    message: str
    data: PaystackTransferData
