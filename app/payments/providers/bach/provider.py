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
from app.payments.providers.bach.client import BachClient
from app.payments.providers.bach.mapper import BachMapper


class BachProvider(PaymentProvider):
    def __init__(self, client: BachClient) -> None:
        self.client = client

    async def collect(self, request: CheckoutRequest) -> CheckoutResponse:
        payload = BachMapper.to_checkout_request(
            request=request,
            reference=self._generate_reference(),
        )
        response = await self.client.create_checkout(payload)
        return BachMapper.from_checkout_response(response, request)

    async def disburse(self, request: DisbursementRequest) -> DisbursementResponse:
        destination = await self.client.create_payout_destination(
            BachMapper.to_payout_destination_request(request)
        )
        if not destination["is_usable"]:
            raise ValueError(
                "Bachs payout destination "
                f"{destination['id']} is not usable (status: {destination['status']})"
            )

        reference = self._generate_reference()
        payout = await self.client.create_payout(
            payload=BachMapper.to_payout_request(
                request=request,
                destination_id=destination["id"],
                reference=reference,
            ),
            idempotency_key=reference,
        )
        return BachMapper.from_payout_response(payout, request)

    async def verify(self, request: VerificationRequest) -> VerificationResponse:
        response = await self.client.retrieve_checkout(request.reference)
        return BachMapper.from_verification_response(response)

    def _generate_reference(self) -> str:
        return f"railswitch-{uuid4().hex}"
