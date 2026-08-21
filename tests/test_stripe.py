import asyncio

import pytest

from app.payments.contracts import (
    CheckoutRequest,
    CheckoutResponse,
    DisbursementRequest,
    DisbursementResponse,
    VerificationRequest,
    VerificationResponse,
)
from app.payments.contracts import (
    PaymentProvider as PaymentProviderContract,
)
from app.payments.enums import (
    CollectionMethod,
    Country,
    Currency,
    PaymentOperation,
    PaymentProvider,
    PaymentStatus,
)
from app.payments.factory import PaymentProviderFactory
from app.payments.providers.stripe.client import StripeClient
from app.payments.providers.stripe.mapper import StripeMapper
from app.payments.providers.stripe.provider import StripeProvider
from app.payments.providers.stripe.types import (
    StripeCheckoutRequest,
    StripeCheckoutSession,
    StripePaymentIntent,
    StripePayout,
)


class StubStripeClient(StripeClient):
    def __init__(self) -> None:
        super().__init__("stripe-key")
        self.payment_intent_called = False
        self.checkout_session_id: str | None = None

    async def create_checkout_session(
        self, payload: StripeCheckoutRequest
    ) -> StripeCheckoutSession:
        return {
            "id": "cs_123",
            "url": "https://checkout.stripe.test",
            "payment_status": "unpaid",
            "amount_total": 5000,
            "currency": "usd",
            "payment_intent": None,
        }

    async def retrieve_checkout_session(self, session_id: str) -> StripeCheckoutSession:
        self.checkout_session_id = session_id
        return {
            "id": session_id,
            "url": "https://checkout.stripe.test",
            "payment_status": "paid",
            "amount_total": 5000,
            "currency": "usd",
            "payment_intent": "pi_123",
        }

    async def retrieve_payment_intent(
        self, payment_intent_id: str
    ) -> StripePaymentIntent:
        self.payment_intent_called = True
        return {"status": "succeeded", "amount": 5000, "currency": "usd"}

    async def retrieve_payout(self, payout_id: str) -> StripePayout:
        return {"id": payout_id, "status": "paid", "amount": 5000, "currency": "cad"}


def request(
    country: Country = Country.UNITED_STATES, currency: Currency = Currency.USD
) -> CheckoutRequest:
    return CheckoutRequest(
        country, 5000, currency, "buyer@example.test", [CollectionMethod.CARD]
    )


class StubPaymentProvider(PaymentProviderContract):
    async def collect(self, request: CheckoutRequest) -> CheckoutResponse:
        raise NotImplementedError

    async def disburse(self, request: DisbursementRequest) -> DisbursementResponse:
        raise NotImplementedError

    async def verify(self, request: VerificationRequest) -> VerificationResponse:
        raise NotImplementedError


def test_factory_routes_us_and_canada_to_stripe() -> None:
    stripe = StubPaymentProvider()
    factory = PaymentProviderFactory(
        StubPaymentProvider(), StubPaymentProvider(), stripe
    )
    assert factory.get_provider(Country.UNITED_STATES) is stripe
    assert factory.get_provider(Country.CANADA) is stripe


def test_checkout_payload_uses_minor_units_and_lowercase_currency() -> None:
    payload = StripeMapper.to_checkout_request(
        request(), "https://success", "https://cancel"
    )
    assert "'currency': 'usd'" in str(payload["line_items"])
    assert "'unit_amount': 5000" in str(payload["line_items"])
    canada_payload = StripeMapper.to_checkout_request(
        request(Country.CANADA, Currency.CAD), "s", "c"
    )
    assert "'currency': 'cad'" in str(canada_payload["line_items"])
    with pytest.raises(ValueError, match="mobile_money"):
        StripeMapper.to_checkout_request(
            CheckoutRequest(
                Country.UNITED_STATES,
                1,
                Currency.USD,
                "a@b.test",
                [CollectionMethod.MOBILE_MONEY],
            ),
            "s",
            "c",
        )


def test_stripe_maps_caller_reference_and_metadata() -> None:
    checkout_request = request()
    checkout_request.reference = "ORD-123"
    checkout_request.metadata = {"order_id": "ORD-123"}

    payload = StripeMapper.to_checkout_request(checkout_request, "s", "c")

    assert payload.get("client_reference_id") == "ORD-123"
    assert payload.get("metadata") == {"order_id": "ORD-123"}


def test_stripe_provider_collects_and_verifies_by_operation() -> None:
    client = StubStripeClient()
    provider = StripeProvider(client, "https://success", "https://cancel")
    checkout_request = request()
    checkout_request.reference = "PAY-456"
    checkout = asyncio.run(provider.collect(checkout_request))
    verification = asyncio.run(
        provider.verify(
            VerificationRequest(
                checkout.provider_reference,
                PaymentProvider.STRIPE,
                Country.UNITED_STATES,
                PaymentOperation.COLLECTION,
            )
        )
    )
    payout = asyncio.run(
        provider.verify(
            VerificationRequest(
                "po_123",
                PaymentProvider.STRIPE,
                Country.CANADA,
                PaymentOperation.DISBURSEMENT,
            )
        )
    )
    assert checkout.status is PaymentStatus.PENDING
    assert checkout.reference == "PAY-456"
    assert checkout.reference != checkout.provider_reference
    assert verification.status is PaymentStatus.SUCCESS and client.payment_intent_called
    assert client.checkout_session_id == checkout.provider_reference
    assert payout.status is PaymentStatus.SUCCESS and payout.currency is Currency.CAD
