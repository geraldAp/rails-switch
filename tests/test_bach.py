import asyncio
from typing import Self

import pytest

from app.payments.config import settings
from app.payments.contracts import (
    CheckoutRequest,
    DisbursementRequest,
    VerificationRequest,
)
from app.payments.dependencies import build_payment_service
from app.payments.enums import (
    CollectionMethod,
    Country,
    Currency,
    DisbursementMethod,
    PaymentOperation,
    PaymentProvider,
    PaymentStatus,
)
from app.payments.providers.bach.client import BachClient
from app.payments.providers.bach.mapper import BachMapper
from app.payments.providers.bach.provider import BachProvider
from app.payments.providers.bach.types import (
    BachCheckoutDetails,
    BachCheckoutRequest,
    BachCheckoutResponse,
    BachPayoutDestinationRequest,
    BachPayoutDestinationResponse,
    BachPayoutDetails,
    BachPayoutRequest,
    BachPayoutResponse,
)


def checkout_request(
    methods: list[CollectionMethod] | None = None,
) -> CheckoutRequest:
    return CheckoutRequest(
        country=Country.NIGERIA,
        amount_minor=5_000,
        currency=Currency.NGN,
        email="customer@example.test",
        customer_name="Ada Lovelace",
        payment_methods=methods,
    )


def disbursement_request() -> DisbursementRequest:
    return DisbursementRequest(
        country=Country.NIGERIA,
        amount_minor=500_000,
        currency=Currency.NGN,
        method=DisbursementMethod.BANK_ACCOUNT,
        account_number="0123456789",
        bank_code="058",
        account_name="Ada Lovelace",
    )


class StubBachClient(BachClient):
    def __init__(self, is_usable: bool = True) -> None:
        super().__init__(api_key="test-key")
        self.is_usable = is_usable
        self.payout_called = False
        self.payout_reference: str | None = None
        self.payout_id: str | None = None
        self.checkout_id: str | None = None

    async def create_checkout(
        self, payload: BachCheckoutRequest
    ) -> BachCheckoutResponse:
        return {
            "checkout_id": "chk_123",
            "reference": payload["reference"],
            "status": "open",
            "amount": payload["pricing"]["amount"],
            "currency": payload["pricing"]["currency"],
            "checkout_url": "https://checkout.bachs.test/chk_123",
        }

    async def retrieve_checkout(self, checkout_id: str) -> BachCheckoutDetails:
        self.checkout_id = checkout_id
        return {
            "checkout_id": checkout_id,
            "status": "completed",
            "payment_status": "succeeded",
            "amount": "50.00",
            "currency": "NGN",
        }

    async def create_payout_destination(
        self, payload: BachPayoutDestinationRequest
    ) -> BachPayoutDestinationResponse:
        return {
            "id": "pd_123",
            "status": "approved" if self.is_usable else "pending_review",
            "is_usable": self.is_usable,
        }

    async def create_payout(
        self, payload: BachPayoutRequest, idempotency_key: str
    ) -> BachPayoutResponse:
        self.payout_called = True
        assert idempotency_key == payload["reference"]
        self.payout_reference = payload["reference"]
        return {
            "id": "pay_123",
            "status": "pending",
            "amount": payload["amount"],
            "currency": "NGN",
            "reference": payload["reference"],
        }

    async def get_payout(self, withdrawal_id: str) -> BachPayoutDetails:
        self.payout_id = withdrawal_id
        return {
            "id": withdrawal_id,
            "status": "completed",
            "amount": "5000.00",
            "currency": "NGN",
            "reference": "railswitch-payout",
        }


def test_mapper_converts_minor_amounts_without_floats() -> None:
    assert BachMapper.minor_to_decimal(5_000) == "50.00"
    assert BachMapper.decimal_to_minor("50.00") == 5_000
    with pytest.raises(ValueError, match="more than two"):
        BachMapper.decimal_to_minor("50.001")


def test_mapper_maps_compatible_checkout_methods() -> None:
    payload = BachMapper.to_checkout_request(
        checkout_request(
            [
                CollectionMethod.CARD,
                CollectionMethod.BANK_TRANSFER,
                CollectionMethod.MOBILE_MONEY,
            ]
        ),
        reference="railswitch-reference",
    )

    assert payload["pricing"]["amount"] == "50.00"
    assert payload["customer"] == {
        "email": "customer@example.test",
        "name": "Ada Lovelace",
    }
    assert payload.get("allowed_payment_method_types") == [
        "card",
        "bank_transfer",
        "mobile_money",
    ]
    with pytest.raises(ValueError, match="ussd"):
        BachMapper.to_checkout_request(
            checkout_request([CollectionMethod.USSD]), "railswitch-reference"
        )


def test_bach_maps_optional_metadata_and_caller_reference() -> None:
    request = checkout_request()
    request.reference = "ORD-123"
    request.metadata = {"order_id": "ORD-123"}
    payload = BachMapper.to_checkout_request(request, request.reference)

    assert payload.get("metadata") == {"order_id": "ORD-123"}
    assert (
        BachMapper.to_payout_request(
            disbursement_request(), "pd_123", "railswitch-payout"
        )["reference"]
        == "railswitch-payout"
    )


def test_bach_requires_a_customer_name_for_checkout() -> None:
    request = checkout_request()
    request.customer_name = None

    with pytest.raises(ValueError, match="Customer name"):
        BachMapper.to_checkout_request(request, "railswitch-reference")


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        ("succeeded", PaymentStatus.SUCCESS),
        ("accepted", PaymentStatus.SUCCESS),
        ("failed", PaymentStatus.FAILED),
        ("expired", PaymentStatus.FAILED),
        ("created", PaymentStatus.PENDING),
        ("processing", PaymentStatus.PENDING),
        ("underpaid", PaymentStatus.PENDING),
    ],
)
def test_mapper_normalizes_verification_statuses(
    status: str, expected: PaymentStatus
) -> None:
    response: BachCheckoutDetails = {
        "checkout_id": "chk_123",
        "status": "completed",
        "payment_status": status,
        "amount": "50.00",
        "currency": "NGN",
    }

    assert BachMapper.from_verification_response(response).status is expected


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        ("pending", PaymentStatus.PENDING),
        ("processing", PaymentStatus.PENDING),
        ("completed", PaymentStatus.SUCCESS),
        ("failed", PaymentStatus.FAILED),
    ],
)
def test_mapper_normalizes_payout_statuses(
    status: str, expected: PaymentStatus
) -> None:
    response: BachPayoutDetails = {
        "id": "pay_123",
        "status": status,
        "amount": "50.00",
        "currency": "NGN",
        "reference": "payout-123",
    }

    assert BachMapper.from_payout_verification_response(response).status is expected


def test_provider_uses_checkout_id_for_verification() -> None:
    client = StubBachClient()
    provider = BachProvider(client)
    request = checkout_request([CollectionMethod.CARD])
    request.reference = "PAY-456"
    checkout = asyncio.run(provider.collect(request))
    verification = asyncio.run(
        provider.verify(
            VerificationRequest(
                provider_reference=checkout.provider_reference,
                provider=PaymentProvider.BACH,
                country=Country.NIGERIA,
                operation=PaymentOperation.COLLECTION,
            )
        )
    )

    assert checkout.reference == "PAY-456"
    assert checkout.provider_reference == "chk_123"
    assert checkout.reference != checkout.provider_reference
    assert client.checkout_id == checkout.provider_reference
    assert checkout.status is PaymentStatus.PENDING
    assert verification.status is PaymentStatus.SUCCESS
    assert verification.amount_minor == 5_000


def test_provider_uses_payout_id_for_disbursement_verification() -> None:
    client = StubBachClient()
    provider = BachProvider(client)
    payout = asyncio.run(provider.disburse(disbursement_request()))

    verification = asyncio.run(
        provider.verify(
            VerificationRequest(
                provider_reference=payout.provider_reference,
                provider=PaymentProvider.BACH,
                country=Country.NIGERIA,
                operation=PaymentOperation.DISBURSEMENT,
            )
        )
    )

    assert client.payout_id == payout.provider_reference == "pay_123"
    assert verification.provider_reference == payout.provider_reference
    assert verification.status is PaymentStatus.SUCCESS
    assert verification.raw_response is not None
    assert verification.raw_response["id"] == payout.provider_reference


def test_provider_does_not_create_payout_for_unusable_destination() -> None:
    client = StubBachClient(is_usable=False)
    provider = BachProvider(client)

    with pytest.raises(ValueError, match="pd_123.*pending_review"):
        asyncio.run(provider.disburse(disbursement_request()))
    assert not client.payout_called


def test_provider_uses_one_reference_for_payout_and_idempotency() -> None:
    client = StubBachClient()
    response = asyncio.run(BachProvider(client).disburse(disbursement_request()))

    assert response.status is PaymentStatus.PENDING
    assert response.reference == client.payout_reference
    assert response.provider_reference == "pay_123"


def test_client_sends_payout_idempotency_header(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, object]] = []

    class Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> object:
            return {
                "id": "pay_123",
                "status": "pending",
                "amount": "5000.00",
                "currency": "NGN",
                "reference": "payout-123",
            }

    class AsyncClient:
        async def __aenter__(self) -> Self:
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def post(self, url: str, **kwargs: object) -> Response:
            calls.append({"url": url, **kwargs})
            return Response()

    monkeypatch.setattr(
        "app.payments.providers.bach.client.httpx2.AsyncClient", AsyncClient
    )
    client = BachClient(api_key="bach-key", base_url="https://sandbox.bachs.test")
    payload: BachPayoutRequest = {
        "destination": "pd_123",
        "amount": "5000.00",
        "reference": "railswitch-payout",
    }

    asyncio.run(client.create_payout(payload, idempotency_key=payload["reference"]))

    assert calls == [
        {
            "url": "https://sandbox.bachs.test/v1/payouts",
            "headers": {
                "Authorization": "Bearer bach-key",
                "Content-Type": "application/json",
                "Idempotency-Key": "railswitch-payout",
            },
            "json": payload,
        }
    ]


def test_client_gets_payout_by_withdrawal_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, object]] = []

    class Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> object:
            return {
                "id": "pay_123",
                "status": "completed",
                "amount": "5000.00",
                "currency": "NGN",
                "reference": "payout-123",
            }

    class AsyncClient:
        async def __aenter__(self) -> Self:
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def get(self, url: str, **kwargs: object) -> Response:
            calls.append({"url": url, **kwargs})
            return Response()

    monkeypatch.setattr(
        "app.payments.providers.bach.client.httpx2.AsyncClient", AsyncClient
    )
    client = BachClient(api_key="bach-key", base_url="https://sandbox.bachs.test")

    asyncio.run(client.get_payout("pay_123"))

    assert calls == [
        {
            "url": "https://sandbox.bachs.test/v1/payouts/pay_123",
            "headers": {
                "Authorization": "Bearer bach-key",
                "Content-Type": "application/json",
            },
        }
    ]


def test_dependencies_build_all_providers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "paystack_gh_secret_key", "ghana-key")
    monkeypatch.setattr(settings, "paystack_za_secret_key", "south-africa-key")
    monkeypatch.setattr(settings, "bach_api_key", "bach-key")
    monkeypatch.setattr(settings, "stripe_secret_key", "stripe-key")

    service = build_payment_service()

    assert (
        service.provider_factory.get_provider(Country.NIGERIA).__class__ is BachProvider
    )
