from typing import cast

import httpx2

from app.payments.enums import Country
from app.payments.providers.paystack.types import (
    PaystackCheckoutRequest,
    PaystackCheckoutResponse,
    PaystackTransferRecipientRequest,
    PaystackTransferRecipientResponse,
    PaystackTransferRequest,
    PaystackTransferResponse,
    PaystackVerificationResponse,
)


class PaystackClient:
    def __init__(
        self,
        secrets: dict[Country, str],
        base_url: str = "https://api.paystack.co",
    ):
        self.secrets = secrets
        self.base_url = base_url

    def _get_secret_key(self, country: Country) -> str:
        try:
            return self.secrets[country]
        except KeyError as error:
            raise ValueError(
                f"Paystack is not configured for country {country.value}"
            ) from error

    def _get_headers(self, country: Country) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._get_secret_key(country)}",
            "Content-Type": "application/json",
        }

    # ── COLLECTIONS (CHECKOUT) ─────────────────────────────────────────

    async def initialize_checkout(
        self,
        country: Country,
        payload: PaystackCheckoutRequest,
    ) -> PaystackCheckoutResponse:
        async with httpx2.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/transaction/initialize",
                headers=self._get_headers(country),
                json=payload,
            )

            response.raise_for_status()

            return cast(PaystackCheckoutResponse, response.json())

    # ── TRANSACTION FINDING (VERIFICATION) ─────────────────────────────

    async def verify_transaction(
        self,
        country: Country,
        reference: str,
    ) -> PaystackVerificationResponse:
        async with httpx2.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/transaction/verify/{reference}",
                headers=self._get_headers(country),
            )

            response.raise_for_status()

            return cast(PaystackVerificationResponse, response.json())

    # ── DISBURSEMENTS (TRANSFERS) ──────────────────────────────────────

    async def create_transfer_recipient(
        self,
        country: Country,
        payload: PaystackTransferRecipientRequest,
    ) -> PaystackTransferRecipientResponse:
        async with httpx2.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/transferrecipient",
                headers=self._get_headers(country),
                json=payload,
            )

            response.raise_for_status()

            return cast(PaystackTransferRecipientResponse, response.json())

    async def initiate_transfer(
        self,
        country: Country,
        payload: PaystackTransferRequest,
    ) -> PaystackTransferResponse:
        async with httpx2.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/transfer",
                headers=self._get_headers(country),
                json=payload,
            )

            response.raise_for_status()

            return cast(PaystackTransferResponse, response.json())
