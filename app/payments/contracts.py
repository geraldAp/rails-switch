from app.payments.enums import CollectionMethod, Country, Currency, DisbursementMethod, PaymentProvider as Provider, PaymentStatus
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(slots=True)
class CheckoutRequest:
    country: Country
    amount_minor: int
    currency: Currency
    email: str
    payment_methods: list[CollectionMethod] | None = None


@dataclass(slots=True)
class CheckoutResponse:
    reference: str
    provider: Provider
    status: PaymentStatus
    checkout_url: str
    payment_methods: list[CollectionMethod] | None = None


@dataclass(slots=True)
class DisbursementRequest:
    country: Country
    amount_minor: int
    currency: Currency
    method: DisbursementMethod
    account_number: str
    bank_code: str
    account_name: str | None = None


@dataclass(slots=True)
class DisbursementResponse:
    reference: str
    provider: Provider
    method: DisbursementMethod
    status: PaymentStatus


@dataclass(slots=True)
class VerificationRequest:
    reference: str
    country: Country


@dataclass(slots=True)
class VerificationResponse:
    reference: str
    provider: Provider
    status: PaymentStatus
    amount_minor: int | None = None
    currency: Currency | None = None

class PaymentProvider(ABC):
    @abstractmethod
    async def collect(
        self,
        request: CheckoutRequest,
    ) -> CheckoutResponse:
        pass

    @abstractmethod
    async def disburse(
        self,
        request: DisbursementRequest,
    ) -> DisbursementResponse:
        pass

    @abstractmethod
    async def verify(
        self,
        request: VerificationRequest,
    ) -> VerificationResponse:
        pass