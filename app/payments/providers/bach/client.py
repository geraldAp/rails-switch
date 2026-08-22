from typing import cast

import httpx2

from app.payments.enums import PaymentOperation, PaymentProvider
from app.payments.errors import send_provider_request
from app.payments.providers.bach.errors import parse_error_details
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


class BachClient:
    api_key: str
    base_url: str

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://sandbox-api.bachs.io",
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    @property
    def headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    # ── COLLECTIONS (CHECKOUT) ─────────────────────────────────────────

    async def create_checkout(
        self, payload: BachCheckoutRequest
    ) -> BachCheckoutResponse:
        async with httpx2.AsyncClient() as client:
            response = await send_provider_request(
                client.post(
                    f"{self.base_url}/v1/checkout-sessions",
                    headers=self.headers,
                    json=payload,
                ),
                provider=PaymentProvider.BACH,
                operation=PaymentOperation.COLLECTION,
                error_parser=parse_error_details,
            )
            return cast(BachCheckoutResponse, response.json())

    # ── TRANSACTION FINDING (VERIFICATION) ─────────────────────────────

    async def retrieve_checkout(self, checkout_id: str) -> BachCheckoutDetails:
        async with httpx2.AsyncClient() as client:
            response = await send_provider_request(
                client.get(
                    f"{self.base_url}/v1/checkout-sessions/{checkout_id}",
                    headers=self.headers,
                ),
                provider=PaymentProvider.BACH,
                operation=PaymentOperation.COLLECTION,
                error_parser=parse_error_details,
            )
            return cast(BachCheckoutDetails, response.json())

    async def get_payout(self, withdrawal_id: str) -> BachPayoutDetails:
        async with httpx2.AsyncClient() as client:
            response = await send_provider_request(
                client.get(
                    f"{self.base_url}/v1/payouts/{withdrawal_id}",
                    headers=self.headers,
                ),
                provider=PaymentProvider.BACH,
                operation=PaymentOperation.DISBURSEMENT,
                error_parser=parse_error_details,
            )
            return cast(BachPayoutDetails, response.json())

    # ── DISBURSEMENTS (TRANSFERS) ──────────────────────────────────────

    async def create_payout_destination(
        self, payload: BachPayoutDestinationRequest
    ) -> BachPayoutDestinationResponse:
        async with httpx2.AsyncClient() as client:
            response = await send_provider_request(
                client.post(
                    f"{self.base_url}/v1/payouts/destinations",
                    headers=self.headers,
                    json=payload,
                ),
                provider=PaymentProvider.BACH,
                operation=PaymentOperation.DISBURSEMENT,
                error_parser=parse_error_details,
            )
            return cast(BachPayoutDestinationResponse, response.json())

    async def create_payout(
        self,
        payload: BachPayoutRequest,
        idempotency_key: str,
    ) -> BachPayoutResponse:
        headers = {**self.headers, "Idempotency-Key": idempotency_key}
        async with httpx2.AsyncClient() as client:
            response = await send_provider_request(
                client.post(
                    f"{self.base_url}/v1/payouts",
                    headers=headers,
                    json=payload,
                ),
                provider=PaymentProvider.BACH,
                operation=PaymentOperation.DISBURSEMENT,
                error_parser=parse_error_details,
            )
            return cast(BachPayoutResponse, response.json())
