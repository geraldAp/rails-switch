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
from app.payments.enums import (
    Country,
    Currency,
    DisbursementMethod,
    PaymentOperation,
    PaymentStatus,
)
from app.payments.enums import PaymentProvider as Provider
from app.payments.factory import PaymentProviderFactory
from app.payments.service import PaymentService


class PaymentProviderSpy(PaymentProvider):
    def __init__(self) -> None:
        self.checkout_request: CheckoutRequest | None = None
        self.disbursement_request: DisbursementRequest | None = None
        self.verification_request: VerificationRequest | None = None

    async def collect(self, request: CheckoutRequest) -> CheckoutResponse:
        self.checkout_request = request
        return CheckoutResponse(
            reference=request.reference,
            provider_reference="checkout-provider-reference",
            provider=Provider.PAYSTACK,
            status=PaymentStatus.PENDING,
            checkout_url="https://checkout.example.test",
        )

    async def disburse(self, request: DisbursementRequest) -> DisbursementResponse:
        self.disbursement_request = request
        return DisbursementResponse(
            reference=request.reference,
            provider_reference="disbursement-provider-reference",
            provider=Provider.PAYSTACK,
            method=request.method,
            status=PaymentStatus.PENDING,
        )

    async def verify(self, request: VerificationRequest) -> VerificationResponse:
        self.verification_request = request
        return VerificationResponse(
            request.provider_reference, request.provider, PaymentStatus.PENDING
        )


def test_factory_selects_the_only_provider_for_a_country() -> None:
    paystack = PaymentProviderSpy()
    bach = PaymentProviderSpy()
    stripe = PaymentProviderSpy()
    factory = PaymentProviderFactory(
        {
            Provider.PAYSTACK: paystack,
            Provider.BACH: bach,
            Provider.STRIPE: stripe,
        }
    )

    assert factory.get_provider(Country.GHANA) is paystack
    assert factory.get_provider(Country.SOUTH_AFRICA) is paystack
    assert factory.get_provider(Country.NIGERIA) is bach
    assert factory.get_provider(Country.UNITED_STATES) is stripe
    assert factory.get_provider(Country.CANADA) is stripe


def test_factory_honors_an_explicit_provider_only_when_country_supports_it() -> None:
    paystack = PaymentProviderSpy()
    factory = PaymentProviderFactory({Provider.PAYSTACK: paystack})

    assert factory.get_provider(Country.GHANA, Provider.PAYSTACK) is paystack

    try:
        factory.get_provider(Country.GHANA, Provider.STRIPE)
    except ValueError as error:
        assert str(error) == "Provider 'stripe' is not configured for country GH"
    else:
        raise AssertionError("Expected an incompatible provider to be rejected")


def test_factory_requires_provider_selection_when_country_has_multiple_providers() -> (
    None
):
    paystack = PaymentProviderSpy()
    stripe = PaymentProviderSpy()
    factory = PaymentProviderFactory(
        {Provider.PAYSTACK: paystack, Provider.STRIPE: stripe},
        routes={Country.GHANA: {Provider.PAYSTACK, Provider.STRIPE}},
    )

    try:
        factory.get_provider(Country.GHANA)
    except ValueError as error:
        assert str(error) == (
            "Multiple providers are configured for country GH; specify a provider"
        )
    else:
        raise AssertionError("Expected provider selection to be required")

    assert factory.get_provider(Country.GHANA, Provider.STRIPE) is stripe


def test_collect_and_disburse_forward_optional_provider_to_factory() -> None:
    paystack = PaymentProviderSpy()
    service = PaymentService(PaymentProviderFactory({Provider.PAYSTACK: paystack}))

    checkout = CheckoutRequest(
        country=Country.GHANA,
        currency=Currency.GHS,
        amount_minor=1000,
        email="buyer@example.com",
        provider=Provider.PAYSTACK,
    )
    disbursement = DisbursementRequest(
        country=Country.GHANA,
        currency=Currency.GHS,
        amount_minor=1000,
        method=DisbursementMethod.BANK_ACCOUNT,
        account_number="1234567890",
        bank_code="001",
        provider=Provider.PAYSTACK,
    )

    asyncio.run(service.collect(checkout))
    asyncio.run(service.disburse(disbursement))

    assert paystack.checkout_request is checkout
    assert paystack.disbursement_request is disbursement

    incompatible_disbursement = DisbursementRequest(
        country=Country.GHANA,
        currency=Currency.GHS,
        amount_minor=1000,
        method=DisbursementMethod.BANK_ACCOUNT,
        account_number="1234567890",
        bank_code="001",
        provider=Provider.STRIPE,
    )
    try:
        asyncio.run(service.disburse(incompatible_disbursement))
    except ValueError as error:
        assert str(error) == "Provider 'stripe' is not configured for country GH"
    else:
        raise AssertionError("Expected incompatible provider selection to fail")


def test_collection_rejects_provider_configured_for_a_different_country() -> None:
    service = PaymentService(
        PaymentProviderFactory(
            {
                Provider.PAYSTACK: PaymentProviderSpy(),
                Provider.STRIPE: PaymentProviderSpy(),
            }
        )
    )
    request = CheckoutRequest(
        country=Country.GHANA,
        currency=Currency.GHS,
        amount_minor=1000,
        email="buyer@example.com",
        provider=Provider.STRIPE,
    )

    try:
        asyncio.run(service.collect(request))
    except ValueError as error:
        assert str(error) == "Provider 'stripe' is not configured for country GH"
    else:
        raise AssertionError("Expected incompatible provider selection to fail")


def test_factory_explains_when_an_allowed_provider_was_not_generated() -> None:
    factory = PaymentProviderFactory({}, routes={Country.GHANA: {Provider.PAYSTACK}})

    try:
        factory.get_provider(Country.GHANA, Provider.PAYSTACK)
    except ValueError as error:
        assert str(error) == "Provider 'paystack' was not generated"
    else:
        raise AssertionError("Expected a missing generated provider to fail")


def test_verify_forwards_the_request_to_the_selected_provider() -> None:
    paystack = PaymentProviderSpy()
    service = PaymentService(
        PaymentProviderFactory(
            {
                Provider.PAYSTACK: paystack,
                Provider.BACH: PaymentProviderSpy(),
                Provider.STRIPE: PaymentProviderSpy(),
            }
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
