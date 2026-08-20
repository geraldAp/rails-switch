from enum import StrEnum


class PaymentStatus(StrEnum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"


class PaymentProvider(StrEnum):
    PAYSTACK = "paystack"
    BACH = "bach"


class Country(StrEnum):
    GHANA = "GH"
    NIGERIA = "NG"
    SOUTH_AFRICA = "ZA"


class Currency(StrEnum):
    GHS = "GHS"
    NGN = "NGN"
    ZAR = "ZAR"