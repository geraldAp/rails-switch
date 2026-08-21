from decimal import Decimal, InvalidOperation

from app.payments.contracts import (
    CheckoutRequest,
    CheckoutResponse,
    DisbursementRequest,
    DisbursementResponse,
    VerificationResponse,
)
from app.payments.enums import (
    CollectionMethod,
    Currency,
    DisbursementMethod,
    PaymentStatus,
)
from app.payments.enums import (
    PaymentProvider as Provider,
)
from app.payments.providers.bach.types import (
    BachCheckoutDetails,
    BachCheckoutRequest,
    BachCheckoutResponse,
    BachPaymentMethod,
    BachPayoutDestinationRequest,
    BachPayoutDetails,
    BachPayoutRequest,
    BachPayoutResponse,
)


class BachMapper:
    # ── COLLECTIONS (CHECKOUT) ─────────────────────────────────────────

    @staticmethod
    def to_checkout_request(
        request: CheckoutRequest, reference: str
    ) -> BachCheckoutRequest:
        payload: BachCheckoutRequest = {
            "pricing": {
                "currency": request.currency.value,
                "amount": BachMapper.minor_to_decimal(request.amount_minor),
            },
            "customer": {"email": request.email},
            "reference": reference,
        }

        if request.payment_methods:
            payload["payment_methods"] = [
                BachMapper._map_collection_method(method)
                for method in request.payment_methods
            ]
        if request.metadata is not None:
            payload["metadata"] = request.metadata

        return payload

    @staticmethod
    def from_checkout_response(
        response: BachCheckoutResponse,
        request: CheckoutRequest,
    ) -> CheckoutResponse:
        # Bachs retrieval requires checkout_id, so this is the only reference
        # callers can later use to verify without persistence.
        return CheckoutResponse(
            reference=request.reference,
            provider_reference=response["checkout_id"],
            provider=Provider.BACH,
            status=PaymentStatus.PENDING,
            checkout_url=response["checkout_url"],
            payment_methods=request.payment_methods,
            metadata=request.metadata,
            raw_response=dict(response),
        )

    # ── DISBURSEMENTS (TRANSFERS) ──────────────────────────────────────

    @staticmethod
    def to_payout_destination_request(
        request: DisbursementRequest,
    ) -> BachPayoutDestinationRequest:
        if request.method is not DisbursementMethod.BANK_ACCOUNT:
            raise ValueError(
                f"Bachs does not support {request.method.value} disbursements"
            )
        if request.account_name is None:
            raise ValueError("Account name is required for Bachs bank payouts")

        payload: BachPayoutDestinationRequest = {
            "currency": request.currency.value,
            "account_number": request.account_number,
            "bank_code": request.bank_code,
            "name": request.account_name,
        }
        if request.metadata is not None:
            payload["metadata"] = request.metadata
        return payload

    @staticmethod
    def to_payout_request(
        request: DisbursementRequest,
        destination_id: str,
        reference: str,
    ) -> BachPayoutRequest:
        payload: BachPayoutRequest = {
            "destination": destination_id,
            "amount": BachMapper.minor_to_decimal(request.amount_minor),
            "reference": request.reference or reference,
        }
        if request.metadata is not None:
            payload["metadata"] = request.metadata
        return payload

    @staticmethod
    def from_payout_response(
        response: BachPayoutResponse,
        request: DisbursementRequest,
    ) -> DisbursementResponse:
        return DisbursementResponse(
            reference=request.reference,
            provider_reference=response["id"],
            provider=Provider.BACH,
            method=request.method,
            status=BachMapper._map_payout_status(response["status"]),
            metadata=request.metadata,
            raw_response=dict(response),
        )

    @staticmethod
    def from_payout_verification_response(
        response: BachPayoutDetails,
    ) -> VerificationResponse:
        return VerificationResponse(
            provider_reference=response["id"],
            provider=Provider.BACH,
            status=BachMapper._map_payout_status(response["status"]),
            amount_minor=BachMapper.decimal_to_minor(response["amount"]),
            currency=Currency(response["currency"]),
            raw_response=dict(response),
        )

    @staticmethod
    def from_verification_response(
        response: BachCheckoutDetails,
    ) -> VerificationResponse:
        return VerificationResponse(
            provider_reference=response["checkout_id"],
            provider=Provider.BACH,
            status=BachMapper._map_payment_status(response.get("payment_status")),
            amount_minor=BachMapper.decimal_to_minor(response["amount"]),
            currency=Currency(response["currency"]),
            raw_response=dict(response),
        )

    @staticmethod
    def minor_to_decimal(amount_minor: int) -> str:
        return format(Decimal(amount_minor) / Decimal(100), ".2f")

    @staticmethod
    def decimal_to_minor(amount: str) -> int:
        try:
            minor_amount = Decimal(amount) * Decimal(100)
        except InvalidOperation as error:
            raise ValueError(f"Invalid Bachs decimal amount: {amount}") from error
        if minor_amount != minor_amount.to_integral_value():
            raise ValueError(f"Bachs amount has more than two decimal places: {amount}")
        return int(minor_amount)

    @staticmethod
    def _map_collection_method(method: CollectionMethod) -> BachPaymentMethod:
        match method:
            case CollectionMethod.CARD:
                return BachPaymentMethod.CARD
            case CollectionMethod.BANK_TRANSFER:
                return BachPaymentMethod.BANK_TRANSFER
            case CollectionMethod.MOBILE_MONEY:
                return BachPaymentMethod.MOBILE_MONEY
            case _:
                raise ValueError(f"Bachs does not support {method.value} checkout")

    @staticmethod
    def _map_payment_status(status: str | None) -> PaymentStatus:
        match status.lower() if status else "created":
            case "succeeded" | "accepted":
                return PaymentStatus.SUCCESS
            case (
                "failed"
                | "expired"
                | "cancelled"
                | "canceled"
                | "refunded"
                | "partially_refunded"
            ):
                return PaymentStatus.FAILED
            case _:
                return PaymentStatus.PENDING

    @staticmethod
    def _map_payout_status(status: str) -> PaymentStatus:
        match status.lower():
            case "completed":
                return PaymentStatus.SUCCESS
            case "failed":
                return PaymentStatus.FAILED
            case _:
                return PaymentStatus.PENDING
