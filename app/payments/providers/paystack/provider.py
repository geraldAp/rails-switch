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
from app.payments.providers.paystack.client import PaystackClient
from app.payments.providers.paystack.mapper import PaystackMapper


class PaystackProvider(PaymentProvider):
    def __init__(
        self,
        client: PaystackClient,
        callback_url: str,
    ):
        self.client = client
        self.callback_url = callback_url

    # ── COLLECTIONS (CHECKOUT) ─────────────────────────────────────────

    async def collect(
        self,
        request: CheckoutRequest,
    ) -> CheckoutResponse:
        payload = PaystackMapper.to_checkout_request(
            request=request,
            callback_url=self.callback_url,
        )

        response = await self.client.initialize_checkout(
            country=request.country,
            payload=payload,
        )

        return PaystackMapper.from_checkout_response(
            response=response,
            request=request,
        )

    # ── DISBURSEMENTS (TRANSFERS) ──────────────────────────────────────

    async def disburse(
        self,
        request: DisbursementRequest,
    ) -> DisbursementResponse:
        recipient_payload = PaystackMapper.to_transfer_recipient_request(
            request=request,
        )

        recipient_response = await self.client.create_transfer_recipient(
            country=request.country,
            payload=recipient_payload,
        )

        recipient_code = recipient_response["data"]["recipient_code"]

        reference = self._generate_reference()

        transfer_payload = PaystackMapper.to_transfer_request(
            request=request,
            recipient_code=recipient_code,
            reference=reference,
        )

        transfer_response = await self.client.initiate_transfer(
            country=request.country,
            payload=transfer_payload,
        )

        return PaystackMapper.from_transfer_response(
            response=transfer_response,
            request=request,
        )

    # ── TRANSACTION FINDING (VERIFICATION) ─────────────────────────────

    async def verify(
        self,
        request: VerificationRequest,
    ) -> VerificationResponse:
        response = await self.client.verify_transaction(
            country=request.country,
            reference=request.reference,
        )

        return PaystackMapper.from_verification_response(
            response=response,
        )

    # ── PRIVATE HELPERS ────────────────────────────────────────────────

    def _generate_reference(self) -> str:
        return f"railswitch-{uuid4().hex}"
