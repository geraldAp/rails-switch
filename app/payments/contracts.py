# app/payments/contracts.py

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(slots=True)
class CheckoutRequest:
    country: str
    amount_minor: int
    currency: str
    email: str


@dataclass(slots=True)
class CheckoutResponse:
    reference: str
    provider: str
    status: str
    checkout_url: str


@dataclass(slots=True)
class DisbursementRequest:
    country: str
    amount_minor: int
    currency: str
    account_number: str
    bank_code: str
    account_name: str | None = None


@dataclass(slots=True)
class DisbursementResponse:
    reference: str
    provider: str
    status: str


@dataclass(slots=True)
class VerificationRequest:
    reference: str


@dataclass(slots=True)
class VerificationResponse:
    reference: str
    provider: str
    status: str
    amount_minor: int | None = None
    currency: str | None = None


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