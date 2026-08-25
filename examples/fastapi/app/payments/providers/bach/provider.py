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
from .client import BachClient
from .mapper import BachMapper


class BachProvider(PaymentProvider):
    def __init__(self, client: BachClient) -> None:
        self.client = client

    # ── COLLECTIONS (CHECKOUT) ─────────────────────────────────────────

    async def collect(self, request: CheckoutRequest) -> CheckoutResponse:
        reference = self._reference_for(request.reference)
        request = replace(request, reference=reference)
        payload = BachMapper.to_checkout_request(
            request=request,
            reference=reference,
        )
        response = await self.client.create_checkout(payload)
        return BachMapper.from_checkout_response(response, request)

    # ── DISBURSEMENTS (TRANSFERS) ──────────────────────────────────────

    async def disburse(self, request: DisbursementRequest) -> DisbursementResponse:
        destination = await self.client.create_payout_destination(
            BachMapper.to_payout_destination_request(request)
        )
        if not destination["is_usable"]:
            raise ValueError(
                "Bachs payout destination "
                f"{destination['id']} is not usable (status: {destination['status']})"
            )

        reference = self._reference_for(request.reference)
        request = replace(request, reference=reference)
        payout = await self.client.create_payout(
            payload=BachMapper.to_payout_request(
                request=request,
                destination_id=destination["id"],
                reference=reference,
            ),
            idempotency_key=reference,
        )
        return BachMapper.from_payout_response(payout, request)

    # ── TRANSACTION FINDING (VERIFICATION) ─────────────────────────────

    async def verify(self, request: VerificationRequest) -> VerificationResponse:
        if request.operation is PaymentOperation.DISBURSEMENT:
            response = await self.client.get_payout(request.provider_reference)
            return BachMapper.from_payout_verification_response(response)
        response = await self.client.retrieve_checkout(request.provider_reference)
        return BachMapper.from_verification_response(response)

    # ── PRIVATE HELPERS ────────────────────────────────────────────────

    def _generate_reference(self) -> str:
        return f"railswitch-{uuid4().hex}"

    def _reference_for(self, caller_reference: str | None) -> str:
        return caller_reference or self._generate_reference()
