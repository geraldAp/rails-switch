import asyncio

from app.payments.contracts import (
    CheckoutRequest,
    CheckoutResponse,
    DisbursementRequest,
    DisbursementResponse,
    PaymentProvider,
    VerificationRequest,
    VerificationResponse,
)
from app.payments.enums import Country, PaymentOperation, PaymentStatus
from app.payments.enums import PaymentProvider as Provider
from app.payments.factory import PaymentProviderFactory
from app.payments.service import PaymentService


class VerificationProviderSpy(PaymentProvider):
    def __init__(self) -> None:
        self.verification_request: VerificationRequest | None = None

    async def collect(self, request: CheckoutRequest) -> CheckoutResponse:
        raise NotImplementedError

    async def disburse(self, request: DisbursementRequest) -> DisbursementResponse:
        raise NotImplementedError

    async def verify(self, request: VerificationRequest) -> VerificationResponse:
        self.verification_request = request
        return VerificationResponse(
            request.provider_reference, request.provider, PaymentStatus.PENDING
        )


def test_factory_routes_countries_and_honors_an_explicit_provider() -> None:
    paystack = VerificationProviderSpy()
    bach = VerificationProviderSpy()
    stripe = VerificationProviderSpy()
    factory = PaymentProviderFactory(
        paystack=paystack,
        bach=bach,
        stripe=stripe,
    )

    assert factory.get_provider(Country.GHANA) is paystack
    assert factory.get_provider(Country.SOUTH_AFRICA) is paystack
    assert factory.get_provider(Country.NIGERIA) is bach
    assert factory.get_provider(Country.UNITED_STATES) is stripe
    assert factory.get_provider(Country.CANADA) is stripe
    assert factory.get_provider(Country.NIGERIA, Provider.PAYSTACK) is paystack


def test_verify_forwards_the_request_to_the_selected_provider() -> None:
    paystack = VerificationProviderSpy()
    service = PaymentService(
        PaymentProviderFactory(
            paystack=paystack,
            bach=VerificationProviderSpy(),
            stripe=VerificationProviderSpy(),
        )
    )
    request = VerificationRequest(
        provider_reference="provider-reference",
        provider=Provider.PAYSTACK,
        country=Country.SOUTH_AFRICA,
        operation=PaymentOperation.COLLECTION,
    )

    response = asyncio.run(service.verify(request))

    assert paystack.verification_request is request
    assert response.provider_reference == request.provider_reference
