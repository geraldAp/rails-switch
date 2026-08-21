from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.payments.enums import (
    CollectionMethod,
    Country,
    Currency,
    DisbursementMethod,
    PaymentOperation,
    PaymentStatus,
)
from app.payments.enums import PaymentProvider as Provider


@dataclass(slots=True)
class CheckoutRequest:
    country: Country
    amount_minor: int
    currency: Currency
    email: str
    payment_methods: list[CollectionMethod] | None = None
    reference: str | None = None
    metadata: dict[str, str] | None = None


@dataclass(slots=True)
class CheckoutResponse:
    reference: str
    provider: Provider
    status: PaymentStatus
    checkout_url: str
    payment_methods: list[CollectionMethod] | None = None
    metadata: dict[str, str] | None = None


@dataclass(slots=True)
class DisbursementRequest:
    country: Country
    amount_minor: int
    currency: Currency
    method: DisbursementMethod
    account_number: str
    bank_code: str
    account_name: str | None = None
    reference: str | None = None
    metadata: dict[str, str] | None = None


@dataclass(slots=True)
class DisbursementResponse:
    reference: str
    provider: Provider
    method: DisbursementMethod
    status: PaymentStatus
    metadata: dict[str, str] | None = None


@dataclass(slots=True)
class VerificationRequest:
    reference: str
    provider: Provider
    country: Country
    operation: PaymentOperation


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
