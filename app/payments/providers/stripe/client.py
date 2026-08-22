from typing import cast

import httpx2

from app.payments.enums import PaymentOperation, PaymentProvider
from app.payments.errors import send_provider_request
from app.payments.providers.stripe.types import (
    StripeCheckoutRequest,
    StripeCheckoutSession,
    StripePaymentIntent,
    StripePayout,
)


class StripeClient:
    def __init__(
        self, secret_key: str, base_url: str = "https://api.stripe.com"
    ) -> None:
        self.secret_key = secret_key
        self.base_url = base_url.rstrip("/")

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.secret_key}"}

    async def create_checkout_session(
        self, payload: StripeCheckoutRequest
    ) -> StripeCheckoutSession:
        async with httpx2.AsyncClient() as client:
            response = await send_provider_request(
                client.post(
                    f"{self.base_url}/v1/checkout/sessions",
                    headers=self.headers,
                    data=_form_data(payload),
                ),
                provider=PaymentProvider.STRIPE,
                operation=PaymentOperation.COLLECTION,
            )
            return cast(StripeCheckoutSession, response.json())

    async def retrieve_checkout_session(self, session_id: str) -> StripeCheckoutSession:
        async with httpx2.AsyncClient() as client:
            response = await send_provider_request(
                client.get(
                    f"{self.base_url}/v1/checkout/sessions/{session_id}",
                    headers=self.headers,
                ),
                provider=PaymentProvider.STRIPE,
                operation=PaymentOperation.COLLECTION,
            )
            return cast(StripeCheckoutSession, response.json())

    async def retrieve_payment_intent(
        self, payment_intent_id: str
    ) -> StripePaymentIntent:
        async with httpx2.AsyncClient() as client:
            response = await send_provider_request(
                client.get(
                    f"{self.base_url}/v1/payment_intents/{payment_intent_id}",
                    headers=self.headers,
                ),
                provider=PaymentProvider.STRIPE,
                operation=PaymentOperation.COLLECTION,
            )
            return cast(StripePaymentIntent, response.json())

    async def retrieve_payout(self, payout_id: str) -> StripePayout:
        async with httpx2.AsyncClient() as client:
            response = await send_provider_request(
                client.get(
                    f"{self.base_url}/v1/payouts/{payout_id}", headers=self.headers
                ),
                provider=PaymentProvider.STRIPE,
                operation=PaymentOperation.DISBURSEMENT,
            )
            return cast(StripePayout, response.json())


def _form_data(payload: StripeCheckoutRequest) -> dict[str, str]:
    """Encode nested Checkout parameters in Stripe's form-style syntax."""
    encoded: dict[str, str] = {}

    def add(value: object, key: str) -> None:
        if isinstance(value, dict):
            for nested_key, nested_value in value.items():
                add(nested_value, f"{key}[{nested_key}]")
        elif isinstance(value, list):
            for index, item in enumerate(value):
                add(item, f"{key}[{index}]")
        else:
            encoded[key] = str(value)

    for key, value in payload.items():
        add(value, key)
    return encoded
