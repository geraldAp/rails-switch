from enum import StrEnum


class PaymentStatus(StrEnum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"


class PaymentProvider(StrEnum):
    PAYSTACK = "paystack"
    BACH = "bach"
    STRIPE = "stripe"


class Country(StrEnum):
    GHANA = "GH"
    NIGERIA = "NG"
    SOUTH_AFRICA = "ZA"
    UNITED_STATES = "US"
    CANADA = "CA"


class Currency(StrEnum):
    GHS = "GHS"
    NGN = "NGN"
    ZAR = "ZAR"
    USD = "USD"
    CAD = "CAD"


class CollectionMethod(StrEnum):
    CARD = "card"
    BANK_TRANSFER = "bank_transfer"
    MOBILE_MONEY = "mobile_money"
    USSD = "ussd"
    QR = "qr"


class DisbursementMethod(StrEnum):
    BANK_ACCOUNT = "bank_account"
    MOBILE_MONEY = "mobile_money"
    DEBIT_CARD = "debit_card"


class PaymentOperation(StrEnum):
    COLLECTION = "collection"
    DISBURSEMENT = "disbursement"
