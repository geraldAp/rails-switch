from dataclasses import replace
from uuid import uuid4

from ...contracts import (
    CheckoutRequest,
    CheckoutResponse,
    DisbursementRequest,
    DisbursementResponse,
    PaymentProvider,
    VerificationRequest,
    VerificationResponse,
)
from ...enums import PaymentOperation
from .client import PaystackClient
from .mapper import PaystackMapper


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
        request = self._with_reference(request)
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

        reference = self._reference_for(request.reference)
        request = replace(request, reference=reference)

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
        if request.operation is PaymentOperation.DISBURSEMENT:
            response = await self.client.verify_transfer(
                country=request.country,
                reference=request.provider_reference,
            )
            return PaystackMapper.from_transfer_verification_response(response)

        response = await self.client.verify_transaction(
            country=request.country,
            reference=request.provider_reference,
        )

        return PaystackMapper.from_verification_response(
            response=response,
        )

    # ── PRIVATE HELPERS ────────────────────────────────────────────────

    def _generate_reference(self) -> str:
        return f"railswitch-{uuid4().hex}"

    def _with_reference(self, request: CheckoutRequest) -> CheckoutRequest:
        return replace(request, reference=self._reference_for(request.reference))

    def _reference_for(self, caller_reference: str | None) -> str:
        return caller_reference or self._generate_reference()
