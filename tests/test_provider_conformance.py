"""Shared normalized contract checks for every supported provider adapter."""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from typing import cast, override

import pytest

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
    CollectionMethod,
    Country,
    Currency,
    DisbursementMethod,
    PaymentOperation,
    PaymentStatus,
)
from app.payments.enums import (
    PaymentProvider as Provider,
)
from app.payments.providers.bach.client import BachClient
from app.payments.providers.bach.provider import BachProvider
from app.payments.providers.bach.types import (
    BachCheckoutDetails,
    BachCheckoutRequest,
    BachCheckoutResponse,
    BachPayoutDestinationRequest,
    BachPayoutDestinationResponse,
    BachPayoutRequest,
    BachPayoutResponse,
)
from app.payments.providers.paystack.client import PaystackClient
from app.payments.providers.paystack.provider import PaystackProvider
from app.payments.providers.paystack.types import (
    PaystackCheckoutRequest,
    PaystackCheckoutResponse,
    PaystackTransferRecipientRequest,
    PaystackTransferRecipientResponse,
    PaystackTransferRequest,
    PaystackTransferResponse,
    PaystackVerificationResponse,
)
from app.payments.providers.stripe.client import StripeClient
from app.payments.providers.stripe.provider import StripeProvider
from app.payments.providers.stripe.types import (
    StripeCheckoutRequest,
    StripeCheckoutSession,
)


class PaystackConformanceClient(PaystackClient):
    def __init__(self) -> None:
        super().__init__({Country.GHANA: "test-key"})

    @override
    async def initialize_checkout(
        self, country: Country, payload: PaystackCheckoutRequest
    ) -> PaystackCheckoutResponse:
        reference = payload.get("reference") or "generated-reference"
        return cast(
            PaystackCheckoutResponse,
            cast(
                object,
                {
                    "status": True,
                    "message": "ok",
                    "data": {
                        "reference": reference,
                        "authorization_url": "https://checkout.example.test/paystack",
                        "access_code": "access-code",
                    },
                },
            ),
        )

    @override
    async def verify_transaction(
        self, country: Country, reference: str
    ) -> PaystackVerificationResponse:
        return cast(
            PaystackVerificationResponse,
            cast(
                object,
                {
                    "status": True,
                    "message": "ok",
                    "data": {
                        "reference": reference,
                        "status": "success",
                        "amount": 5000,
                        "currency": "GHS",
                    },
                },
            ),
        )

    @override
    async def create_transfer_recipient(
        self, country: Country, payload: PaystackTransferRecipientRequest
    ) -> PaystackTransferRecipientResponse:
        return cast(
            PaystackTransferRecipientResponse,
            cast(
                object,
                {
                    "status": True,
                    "message": "ok",
                    "data": {"recipient_code": "recipient-code"},
                },
            ),
        )

    @override
    async def initiate_transfer(
        self, country: Country, payload: PaystackTransferRequest
    ) -> PaystackTransferResponse:
        return cast(
            PaystackTransferResponse,
            cast(
                object,
                {
                    "status": True,
                    "message": "ok",
                    "data": {"reference": payload["reference"], "status": "pending"},
                },
            ),
        )


class BachConformanceClient(BachClient):
    def __init__(self) -> None:
        super().__init__(api_key="test-key")

    @override
    async def create_checkout(
        self, payload: BachCheckoutRequest
    ) -> BachCheckoutResponse:
        return cast(
            BachCheckoutResponse,
            cast(
                object,
                {
                    "checkout_id": "checkout-id",
                    "reference": payload["reference"],
                    "status": "open",
                    "amount": payload["pricing"]["amount"],
                    "currency": "NGN",
                    "checkout_url": "https://checkout.example.test/bach",
                },
            ),
        )

    @override
    async def retrieve_checkout(self, checkout_id: str) -> BachCheckoutDetails:
        return cast(
            BachCheckoutDetails,
            cast(
                object,
                {
                    "checkout_id": checkout_id,
                    "status": "completed",
                    "payment_status": "succeeded",
                    "amount": "50.00",
                    "currency": "NGN",
                },
            ),
        )

    @override
    async def create_payout_destination(
        self, payload: BachPayoutDestinationRequest
    ) -> BachPayoutDestinationResponse:
        return cast(
            BachPayoutDestinationResponse,
            cast(
                object,
                {"id": "destination-id", "status": "approved", "is_usable": True},
            ),
        )

    @override
    async def create_payout(
        self, payload: BachPayoutRequest, idempotency_key: str
    ) -> BachPayoutResponse:
        return cast(
            BachPayoutResponse,
            cast(
                object,
                {
                    "id": "payout-id",
                    "status": "pending",
                    "amount": payload["amount"],
                    "currency": "NGN",
                    "reference": payload["reference"],
                },
            ),
        )


class StripeConformanceClient(StripeClient):
    def __init__(self) -> None:
        super().__init__("test-key")

    @override
    async def create_checkout_session(
        self, payload: StripeCheckoutRequest
    ) -> StripeCheckoutSession:
        return cast(
            StripeCheckoutSession,
            cast(
                object,
                {
                    "id": "session-id",
                    "url": "https://checkout.example.test/stripe",
                    "payment_status": "unpaid",
                    "amount_total": 5000,
                    "currency": "usd",
                    "payment_intent": None,
                },
            ),
        )

    @override
    async def retrieve_checkout_session(self, session_id: str) -> StripeCheckoutSession:
        return cast(
            StripeCheckoutSession,
            cast(
                object,
                {
                    "id": session_id,
                    "url": "https://checkout.example.test/stripe",
                    "payment_status": "paid",
                    "amount_total": 5000,
                    "currency": "usd",
                    "payment_intent": None,
                },
            ),
        )


@dataclass(frozen=True)
class ProviderCase:
    name: str
    provider: Provider
    country: Country
    currency: Currency
    build: Callable[[], PaymentProvider]
    unsupported_method: CollectionMethod | None
    supports_disbursement: bool


CASES = (
    ProviderCase(
        "paystack",
        Provider.PAYSTACK,
        Country.GHANA,
        Currency.GHS,
        lambda: PaystackProvider(
            PaystackConformanceClient(), "https://callback.example.test"
        ),
        None,
        True,
    ),
    ProviderCase(
        "bach",
        Provider.BACH,
        Country.NIGERIA,
        Currency.NGN,
        lambda: BachProvider(BachConformanceClient()),
        CollectionMethod.USSD,
        True,
    ),
    ProviderCase(
        "stripe",
        Provider.STRIPE,
        Country.UNITED_STATES,
        Currency.USD,
        lambda: StripeProvider(
            StripeConformanceClient(),
            "https://success.example.test",
            "https://cancel.example.test",
        ),
        CollectionMethod.MOBILE_MONEY,
        False,
    ),
)
CASE_IDS = tuple(case.name for case in CASES)
UNSUPPORTED_METHOD_CASES = tuple(
    case for case in CASES if case.unsupported_method is not None
)
UNSUPPORTED_METHOD_CASE_IDS = tuple(case.name for case in UNSUPPORTED_METHOD_CASES)


@pytest.mark.parametrize("case", CASES, ids=CASE_IDS)
def test_provider_collection_conforms_to_normalized_contract(
    case: ProviderCase,
) -> None:
    request = CheckoutRequest(
        country=case.country,
        currency=case.currency,
        amount_minor=5000,
        email="buyer@example.test",
        customer_name="Buyer Example",
        payment_methods=[CollectionMethod.CARD],
        reference="order-reference",
        metadata={"order_id": "order-reference"},
    )

    response = asyncio.run(case.build().collect(request))

    assert isinstance(response, CheckoutResponse)
    assert response.reference == "order-reference"
    assert response.provider_reference
    assert response.status in PaymentStatus
    assert response.metadata == {"order_id": "order-reference"}


@pytest.mark.parametrize(
    "case",
    UNSUPPORTED_METHOD_CASES,
    ids=UNSUPPORTED_METHOD_CASE_IDS,
)
def test_provider_rejects_unsupported_collection_methods(case: ProviderCase) -> None:
    unsupported_method = case.unsupported_method
    assert unsupported_method is not None
    request = CheckoutRequest(
        country=case.country,
        currency=case.currency,
        amount_minor=5000,
        email="buyer@example.test",
        customer_name="Buyer Example",
        payment_methods=[unsupported_method],
    )

    with pytest.raises(ValueError, match=unsupported_method.value):
        _ = asyncio.run(case.build().collect(request))


@pytest.mark.parametrize("case", CASES, ids=CASE_IDS)
def test_provider_verification_conforms_to_normalized_contract(
    case: ProviderCase,
) -> None:
    provider = case.build()
    checkout = asyncio.run(
        provider.collect(
            CheckoutRequest(
                country=case.country,
                currency=case.currency,
                amount_minor=5000,
                email="buyer@example.test",
                customer_name="Buyer Example",
                payment_methods=[CollectionMethod.CARD],
                reference="order-reference",
            )
        )
    )

    response = asyncio.run(
        provider.verify(
            VerificationRequest(
                provider_reference=checkout.provider_reference,
                provider=case.provider,
                country=case.country,
                operation=PaymentOperation.COLLECTION,
            )
        )
    )

    assert isinstance(response, VerificationResponse)
    assert response.provider_reference == checkout.provider_reference
    assert response.status in PaymentStatus
    assert response.amount_minor == 5000
    assert response.currency is case.currency


@pytest.mark.parametrize("case", CASES, ids=CASE_IDS)
def test_provider_disbursement_is_supported_or_fails_explicitly(
    case: ProviderCase,
) -> None:
    request = DisbursementRequest(
        country=case.country,
        currency=case.currency,
        amount_minor=5000,
        method=DisbursementMethod.BANK_ACCOUNT,
        account_number="0123456789",
        bank_code="001",
        account_name="Buyer Example",
        reference="payout-reference",
    )

    if not case.supports_disbursement:
        with pytest.raises(ValueError, match="unsupported"):
            _ = asyncio.run(case.build().disburse(request))
        return

    response = asyncio.run(case.build().disburse(request))

    assert isinstance(response, DisbursementResponse)
    assert response.provider_reference
    assert response.status in PaymentStatus
