import asyncio
import re
from typing import cast

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
from app.payments.factory import PaymentProviderFactory
from app.payments.providers.paystack.client import PaystackClient
from app.payments.providers.paystack.mapper import PaystackMapper
from app.payments.providers.paystack.provider import PaystackProvider
from app.payments.providers.paystack.types import (
    PaystackTransferRecipientRequest,
    PaystackTransferRecipientResponse,
    PaystackTransferRequest,
    PaystackTransferResponse,
    PaystackVerificationResponse,
)
from app.payments.service import PaymentService


class StubProvider(PaymentProvider):
    async def collect(self, request: CheckoutRequest) -> CheckoutResponse:
        raise NotImplementedError

    async def disburse(self, request: DisbursementRequest) -> DisbursementResponse:
        raise NotImplementedError

    async def verify(self, request: VerificationRequest) -> VerificationResponse:
        return VerificationResponse(
            request.provider_reference, request.provider, PaymentStatus.PENDING
        )


class StubPaystackClient(PaystackClient):
    def __init__(self) -> None:
        super().__init__(secrets={Country.GHANA: "test-secret"})
        self.transfer_reference: str | None = None
        self.verification_reference: str | None = None
        self.transfer_verification_reference: str | None = None

    async def create_transfer_recipient(
        self,
        country: Country,
        payload: PaystackTransferRecipientRequest,
    ) -> PaystackTransferRecipientResponse:
        return cast(
            PaystackTransferRecipientResponse,
            cast(
                object,
                {
                    "status": True,
                    "message": "ok",
                    "data": {"recipient_code": "RCP_1"},
                },
            ),
        )

    async def initiate_transfer(
        self,
        country: Country,
        payload: PaystackTransferRequest,
    ) -> PaystackTransferResponse:
        self.transfer_reference = payload["reference"]
        return cast(
            PaystackTransferResponse,
            cast(
                object,
                {
                    "status": True,
                    "message": "ok",
                    "data": {
                        "reference": payload["reference"],
                        "status": "pending",
                    },
                },
            ),
        )

    async def verify_transaction(
        self, country: Country, reference: str
    ) -> PaystackVerificationResponse:
        self.verification_reference = reference
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
                        "amount": 100,
                        "currency": "GHS",
                    },
                },
            ),
        )

    async def verify_transfer(
        self, country: Country, reference: str
    ) -> PaystackTransferResponse:
        self.transfer_verification_reference = reference
        return cast(
            PaystackTransferResponse,
            cast(
                object,
                {
                    "status": True,
                    "message": "ok",
                    "data": {
                        "reference": reference,
                        "status": "success",
                        "amount": 100,
                        "currency": "GHS",
                        "domain": "test",
                        "source": "balance",
                        "source_details": None,
                        "reason": None,
                        "failures": None,
                        "transfer_code": "TRF_123",
                        "titan_code": None,
                        "transferred_at": None,
                        "id": 1,
                        "integration": 1,
                        "recipient": 1,
                        "createdAt": "2026-01-01T00:00:00Z",
                        "updatedAt": "2026-01-01T00:00:00Z",
                    },
                },
            ),
        )


def test_factory_selects_one_provider_implementation_per_provider() -> None:
    paystack = StubProvider()
    bach = StubProvider()
    factory = PaymentProviderFactory(
        paystack=paystack,
        bach=bach,
        stripe=StubProvider(),
    )

    assert factory.get_provider(Country.GHANA) is paystack
    assert factory.get_provider(Country.SOUTH_AFRICA) is paystack
    assert factory.get_provider(Country.NIGERIA) is bach
    assert factory.get_provider(Country.NIGERIA, Provider.PAYSTACK) is paystack


def test_verify_uses_requested_provider_and_country() -> None:
    paystack = StubProvider()
    service = PaymentService(
        PaymentProviderFactory(
            paystack=paystack,
            bach=StubProvider(),
            stripe=StubProvider(),
        )
    )
    request = VerificationRequest(
        "reference",
        Provider.PAYSTACK,
        Country.SOUTH_AFRICA,
        PaymentOperation.COLLECTION,
    )

    assert (
        asyncio.run(service.verify(request)).provider_reference
        == request.provider_reference
    )


def test_client_resolves_headers_by_country() -> None:
    client = PaystackClient(
        secrets={
            Country.GHANA: "ghana-secret",
            Country.SOUTH_AFRICA: "south-africa-secret",
        }
    )

    assert client._get_headers(Country.GHANA)["Authorization"] == "Bearer ghana-secret"
    assert (
        client._get_headers(Country.SOUTH_AFRICA)["Authorization"]
        == "Bearer south-africa-secret"
    )
    with pytest.raises(ValueError, match="NG"):
        client._get_secret_key(Country.NIGERIA)


@pytest.mark.parametrize(
    ("country", "recipient_type"),
    [
        (Country.GHANA, "ghipss"),
        (Country.NIGERIA, "nuban"),
        (Country.SOUTH_AFRICA, "basa"),
    ],
)
def test_bank_account_recipient_type_is_country_specific(
    country: Country, recipient_type: str
) -> None:
    request = DisbursementRequest(
        country, 100, Currency.GHS, DisbursementMethod.BANK_ACCOUNT, "123", "001", "Ada"
    )

    assert (
        PaystackMapper.to_transfer_recipient_request(request)["type"] == recipient_type
    )


def test_debit_card_disbursements_are_rejected() -> None:
    request = DisbursementRequest(
        Country.GHANA,
        100,
        Currency.GHS,
        DisbursementMethod.DEBIT_CARD,
        "123",
        "001",
        "Ada",
    )

    with pytest.raises(ValueError, match="not supported"):
        PaystackMapper.to_transfer_recipient_request(request)


def test_checkout_response_starts_pending() -> None:
    response = PaystackMapper.from_checkout_response(
        {
            "status": True,
            "message": "ok",
            "data": {
                "reference": "ref",
                "authorization_url": "https://example.test",
                "access_code": "code",
            },
        },
        CheckoutRequest(
            country=Country.GHANA,
            amount_minor=100,
            currency=Currency.GHS,
            email="ada@example.test",
            payment_methods=[CollectionMethod.CARD],
        ),
    )

    assert response.status is PaymentStatus.PENDING


def test_paystack_preserves_caller_reference_and_metadata_in_payload() -> None:
    payload = PaystackMapper.to_checkout_request(
        CheckoutRequest(
            Country.GHANA,
            100,
            Currency.GHS,
            "ada@example.test",
            reference="ORD-123",
            metadata={"order_id": "ORD-123"},
        ),
        "https://example.test",
    )

    assert payload.get("reference") == "ORD-123"
    assert payload.get("metadata") == '{"order_id": "ORD-123"}'


def test_disbursement_generates_one_paystack_compatible_reference() -> None:
    client = StubPaystackClient()
    provider = PaystackProvider(client, "https://example.test/callback")
    request = DisbursementRequest(
        Country.GHANA,
        100,
        Currency.GHS,
        DisbursementMethod.BANK_ACCOUNT,
        "123",
        "001",
        "Ada",
    )

    response = asyncio.run(provider.disburse(request))

    assert client.transfer_reference is not None
    assert response.reference == client.transfer_reference
    assert response.provider_reference == client.transfer_reference
    assert re.fullmatch(r"railswitch-[a-f0-9]{32}", response.provider_reference)


def test_paystack_verification_uses_provider_reference() -> None:
    client = StubPaystackClient()
    provider = PaystackProvider(client, "https://example.test/callback")

    response = asyncio.run(
        provider.verify(
            VerificationRequest(
                provider_reference="provider-ref",
                provider=Provider.PAYSTACK,
                country=Country.GHANA,
                operation=PaymentOperation.COLLECTION,
            )
        )
    )

    assert client.verification_reference == "provider-ref"
    assert response.provider_reference == "provider-ref"


def test_paystack_transfer_verification_uses_provider_reference() -> None:
    client = StubPaystackClient()
    provider = PaystackProvider(client, "https://example.test/callback")

    response = asyncio.run(
        provider.verify(
            VerificationRequest(
                provider_reference="transfer-ref",
                provider=Provider.PAYSTACK,
                country=Country.GHANA,
                operation=PaymentOperation.DISBURSEMENT,
            )
        )
    )

    assert client.transfer_verification_reference == "transfer-ref"
    assert response.provider_reference == "transfer-ref"
