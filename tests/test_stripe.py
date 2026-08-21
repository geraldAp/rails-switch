import asyncio

import pytest

from app.payments.contracts import CheckoutRequest, VerificationRequest
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


def test_factory_routes_us_and_canada_to_stripe() -> None:
    stripe = object()
    factory = PaymentProviderFactory(object(), object(), stripe)  # type: ignore[arg-type]
    assert factory.get_provider(Country.UNITED_STATES) is stripe
    assert factory.get_provider(Country.CANADA) is stripe


def test_checkout_payload_uses_minor_units_and_lowercase_currency() -> None:
    payload = StripeMapper.to_checkout_request(
        request(), "https://success", "https://cancel"
    )
    assert payload["line_items"][0]["price_data"]["unit_amount"] == 5000
    assert payload["line_items"][0]["price_data"]["currency"] == "usd"
    assert (
        StripeMapper.to_checkout_request(
            request(Country.CANADA, Currency.CAD), "s", "c"
        )["line_items"][0]["price_data"]["currency"]
        == "cad"
    )
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


def test_stripe_provider_collects_and_verifies_by_operation() -> None:
    client = StubStripeClient()
    provider = StripeProvider(client, "https://success", "https://cancel")
    checkout = asyncio.run(provider.collect(request()))
    verification = asyncio.run(
        provider.verify(
            VerificationRequest(
                checkout.reference,
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
    assert verification.status is PaymentStatus.SUCCESS and client.payment_intent_called
    assert payout.status is PaymentStatus.SUCCESS and payout.currency is Currency.CAD
