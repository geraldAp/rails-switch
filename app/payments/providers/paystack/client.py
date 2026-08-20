import httpx2

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
        secret_key: str,
        base_url: str = "https://api.paystack.co",
    ):
        self.secret_key = secret_key
        self.base_url = base_url

    @property
    def headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json",
        }

    async def initialize_checkout(
        self,
        payload: PaystackCheckoutRequest,
    ) -> PaystackCheckoutResponse:
        async with httpx2.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/transaction/initialize",
                headers=self.headers,
                json=payload,
            )

            response.raise_for_status()

            return response.json()

    async def verify_transaction(
        self,
        reference: str,
    ) -> PaystackVerificationResponse:
        async with httpx2.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/transaction/verify/{reference}",
                headers=self.headers,
            )

            response.raise_for_status()

            return response.json()

    async def create_transfer_recipient(
        self,
        payload: PaystackTransferRecipientRequest,
    ) -> PaystackTransferRecipientResponse:
        async with httpx2.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/transferrecipient",
                headers=self.headers,
                json=payload,
            )

            response.raise_for_status()

            return response.json()

    async def initiate_transfer(
        self,
        payload: PaystackTransferRequest,
    ) -> PaystackTransferResponse:
        async with httpx2.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/transfer",
                headers=self.headers,
                json=payload,
            )

            response.raise_for_status()

            return response.json()