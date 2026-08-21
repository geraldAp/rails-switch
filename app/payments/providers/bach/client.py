from typing import cast

import httpx2

from app.payments.providers.bach.types import (
    BachCheckoutDetails,
    BachCheckoutRequest,
    BachCheckoutResponse,
    BachPayoutDestinationRequest,
    BachPayoutDestinationResponse,
    BachPayoutRequest,
    BachPayoutResponse,
)


class BachClient:
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
            response = await client.post(
                f"{self.base_url}/v1/checkout-sessions",
                headers=self.headers,
                json=payload,
            )
            response.raise_for_status()
            return cast(BachCheckoutResponse, response.json())

    # ── TRANSACTION FINDING (VERIFICATION) ─────────────────────────────

    async def retrieve_checkout(self, checkout_id: str) -> BachCheckoutDetails:
        async with httpx2.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/v1/checkout-sessions/{checkout_id}",
                headers=self.headers,
            )
            response.raise_for_status()
            return cast(BachCheckoutDetails, response.json())

    # ── DISBURSEMENTS (TRANSFERS) ──────────────────────────────────────

    async def create_payout_destination(
        self, payload: BachPayoutDestinationRequest
    ) -> BachPayoutDestinationResponse:
        async with httpx2.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/v1/payouts/destinations",
                headers=self.headers,
                json=payload,
            )
            response.raise_for_status()
            return cast(BachPayoutDestinationResponse, response.json())

    async def create_payout(
        self,
        payload: BachPayoutRequest,
        idempotency_key: str,
    ) -> BachPayoutResponse:
        headers = {**self.headers, "Idempotency-Key": idempotency_key}
        async with httpx2.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/v1/payouts",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            return cast(BachPayoutResponse, response.json())
