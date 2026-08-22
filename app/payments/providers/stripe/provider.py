from dataclasses import replace
from uuid import uuid4

from app.payments.contracts import (
    CheckoutRequest,
    CheckoutResponse,
    DisbursementRequest,
    DisbursementResponse,
    PaymentProvider,
    VerificationRequest,
    VerificationResponse,
)
from app.payments.enums import PaymentOperation
from app.payments.providers.stripe.client import StripeClient
from app.payments.providers.stripe.mapper import StripeMapper


class StripeProvider(PaymentProvider):
    def __init__(self, client: StripeClient, success_url: str, cancel_url: str) -> None:
        self.client = client
        self.success_url = success_url
        self.cancel_url = cancel_url

    async def collect(self, request: CheckoutRequest) -> CheckoutResponse:
        self._validate_checkout_urls()
        request = replace(request, reference=self._reference_for(request.reference))
        response = await self.client.create_checkout_session(
            StripeMapper.to_checkout_request(request, self.success_url, self.cancel_url)
        )
        return StripeMapper.from_checkout(response, request)

    async def disburse(self, request: DisbursementRequest) -> DisbursementResponse:
        raise ValueError(
            "Stripe payout creation is unsupported: RailSwitch does not identify a configured Stripe external account"
        )

    async def verify(self, request: VerificationRequest) -> VerificationResponse:
        if request.operation is PaymentOperation.DISBURSEMENT:
            return StripeMapper.from_payout(
                await self.client.retrieve_payout(request.provider_reference)
            )
        session = await self.client.retrieve_checkout_session(
            request.provider_reference
        )
        payment_intent = (
            await self.client.retrieve_payment_intent(session["payment_intent"])
            if session["payment_intent"]
            else None
        )
        return StripeMapper.from_collection(session, payment_intent)

    def _generate_reference(self) -> str:
        return f"railswitch-{uuid4().hex}"

    def _reference_for(self, caller_reference: str | None) -> str:
        return caller_reference or self._generate_reference()

    def _validate_checkout_urls(self) -> None:
        missing = [
            name
            for name, value in (
                ("STRIPE_SUCCESS_URL", self.success_url),
                ("STRIPE_CANCEL_URL", self.cancel_url),
            )
            if not value.strip()
        ]
        if missing:
            raise ValueError(
                "Missing Stripe Checkout redirect URL configuration: "
                + ", ".join(missing)
            )
