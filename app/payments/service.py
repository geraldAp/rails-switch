# app/payments/service.py

from app.payments.contracts import (
    CheckoutRequest,
    CheckoutResponse,
    DisbursementRequest,
    DisbursementResponse,
    VerificationRequest,
    VerificationResponse,
)
from app.payments.factory import PaymentProviderFactory


class PaymentService:
    def __init__(self, provider_factory: PaymentProviderFactory):
        self.provider_factory = provider_factory

    async def collect(
        self,
        request: CheckoutRequest,
    ) -> CheckoutResponse:
        provider = self.provider_factory.get_provider(
            country=request.country,
        )

        return await provider.collect(request)

    async def disburse(
        self,
        request: DisbursementRequest,
    ) -> DisbursementResponse:
        provider = self.provider_factory.get_provider(
            country=request.country,
        )

        return await provider.disburse(request)

    async def verify(
        self,
        request: VerificationRequest,
    ) -> VerificationResponse:
        provider = self.provider_factory.get_provider(
            country=request.country,
            provider=request.provider,
        )

        return await provider.verify(request)
