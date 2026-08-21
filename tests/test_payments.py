import asyncio
import re
from typing import cast

import pytest

from app.payments.contracts import (
    CheckoutRequest,
    DisbursementRequest,
    PaymentProvider,
    VerificationRequest,
)
from app.payments.enums import (
    CollectionMethod,
    Country,
    Currency,
    DisbursementMethod,
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
)
from app.payments.service import PaymentService


class StubProvider(PaymentProvider):
    async def collect(self, request):
        raise NotImplementedError

    async def disburse(self, request):
        raise NotImplementedError

    async def verify(self, request):
        return request


class StubPaystackClient(PaystackClient):
    def __init__(self) -> None:
        super().__init__(secrets={Country.GHANA: "test-secret"})
        self.transfer_reference: str | None = None

    async def create_transfer_recipient(
        self,
        country: Country,
        payload: PaystackTransferRecipientRequest,
    ) -> PaystackTransferRecipientResponse:
        return cast(
            PaystackTransferRecipientResponse,
            {
                "status": True,
                "message": "ok",
                "data": {"recipient_code": "RCP_1"},
            },
        )

    async def initiate_transfer(
        self,
        country: Country,
        payload: PaystackTransferRequest,
    ) -> PaystackTransferResponse:
        self.transfer_reference = payload["reference"]
        return cast(
            PaystackTransferResponse,
            {
                "status": True,
                "message": "ok",
                "data": {
                    "reference": payload["reference"],
                    "status": "pending",
                },
            },
        )


def test_factory_selects_one_provider_implementation_per_provider() -> None:
    paystack = StubProvider()
    bach = StubProvider()
    factory = PaymentProviderFactory(
        paystack=paystack,
        bach=bach,
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
        )
    )
    request = VerificationRequest("reference", Provider.PAYSTACK, Country.SOUTH_AFRICA)

    assert asyncio.run(service.verify(request)) is request


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
    assert re.fullmatch(r"railswitch-[a-f0-9]{32}", response.reference)
