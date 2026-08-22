from typing import cast

import httpx2

from app.payments.enums import PaymentOperation, PaymentProvider
from app.payments.errors import send_provider_request
from app.payments.providers.stripe.errors import parse_error_details
from app.payments.providers.stripe.types import (
    StripeCheckoutRequest,
    StripeCheckoutSession,
    StripePaymentIntent,
    StripePayout,
)


class StripeClient:
    secret_key: str
    base_url: str

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
                error_parser=parse_error_details,
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
                error_parser=parse_error_details,
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
                error_parser=parse_error_details,
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
                error_parser=parse_error_details,
            )
            return cast(StripePayout, response.json())


def _form_data(payload: StripeCheckoutRequest) -> dict[str, str]:
    """Encode nested Checkout parameters in Stripe's form-style syntax."""
    encoded: dict[str, str] = {}

    def add(value: object, key: str) -> None:
        if isinstance(value, dict):
            for nested_key, nested_value in cast(dict[str, object], value).items():
                add(nested_value, f"{key}[{nested_key}]")
        elif isinstance(value, list):
            for index, item in enumerate(cast(list[object], value)):
                add(item, f"{key}[{index}]")
        else:
            encoded[key] = str(value)

    for key, value in cast(dict[str, object], cast(object, payload)).items():
        add(value, key)
    return encoded
