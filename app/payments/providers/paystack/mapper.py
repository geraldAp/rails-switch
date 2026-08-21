import json

from app.payments.contracts import (
    CheckoutRequest,
    CheckoutResponse,
    DisbursementRequest,
    DisbursementResponse,
    VerificationResponse,
)
from app.payments.enums import (
    CollectionMethod,
    Country,
    Currency,
    DisbursementMethod,
    PaymentStatus,
)
from app.payments.enums import (
    PaymentProvider as Provider,
)
from app.payments.providers.paystack.types import (
    PaystackChannel,
    PaystackCheckoutRequest,
    PaystackCheckoutResponse,
    PaystackRecipientType,
    PaystackTransferRecipientRequest,
    PaystackTransferRequest,
    PaystackTransferResponse,
    PaystackVerificationResponse,
)


class PaystackMapper:
    # ── COLLECTIONS (CHECKOUT) ─────────────────────────────────────────

    @staticmethod
    def to_checkout_request(
        request: CheckoutRequest,
        callback_url: str,
    ) -> PaystackCheckoutRequest:
        payload: PaystackCheckoutRequest = {
            "amount": str(request.amount_minor),
            "email": request.email,
            "currency": request.currency.value,
            "callback_url": callback_url,
        }

        if request.payment_methods:
            payload["channels"] = [
                PaystackMapper._map_collection_method(method)
                for method in request.payment_methods
            ]
        if request.reference is not None:
            payload["reference"] = request.reference
        if request.metadata is not None:
            payload["metadata"] = json.dumps(request.metadata)

        return payload

    @staticmethod
    def from_checkout_response(
        response: PaystackCheckoutResponse,
        request: CheckoutRequest,
    ) -> CheckoutResponse:
        return CheckoutResponse(
            reference=request.reference,
            provider_reference=response["data"]["reference"],
            provider=Provider.PAYSTACK,
            status=PaymentStatus.PENDING,
            checkout_url=response["data"]["authorization_url"],
            payment_methods=request.payment_methods,
            metadata=request.metadata,
            raw_response=dict(response),
        )

    # ── DISBURSEMENTS (TRANSFERS) ──────────────────────────────────────

    @staticmethod
    def to_transfer_recipient_request(
        request: DisbursementRequest,
    ) -> PaystackTransferRecipientRequest:
        if request.account_name is None:
            raise ValueError("Account name is required for Paystack disbursements")

        return {
            "type": PaystackMapper._get_recipient_type(request),
            "name": request.account_name,
            "account_number": request.account_number,
            "bank_code": request.bank_code,
            "currency": request.currency.value,
        }

    @staticmethod
    def to_transfer_request(
        request: DisbursementRequest,
        recipient_code: str,
        reference: str,
    ) -> PaystackTransferRequest:
        return {
            "source": "balance",
            "amount": request.amount_minor,
            "recipient": recipient_code,
            "reference": reference,
            "currency": request.currency.value,
        }

    @staticmethod
    def from_transfer_response(
        response: PaystackTransferResponse,
        request: DisbursementRequest,
    ) -> DisbursementResponse:
        return DisbursementResponse(
            reference=request.reference,
            provider_reference=response["data"]["reference"],
            provider=Provider.PAYSTACK,
            method=request.method,
            status=PaystackMapper._map_status(response["data"]["status"]),
            metadata=request.metadata,
            raw_response=dict(response),
        )

    @staticmethod
    def from_verification_response(
        response: PaystackVerificationResponse,
    ) -> VerificationResponse:
        data = response["data"]

        return VerificationResponse(
            provider_reference=data["reference"],
            provider=Provider.PAYSTACK,
            status=PaystackMapper._map_status(data["status"]),
            amount_minor=data["amount"],
            currency=Currency(data["currency"]),
            raw_response=dict(response),
        )

    @staticmethod
    def _map_collection_method(
        method: CollectionMethod,
    ) -> PaystackChannel:
        match method:
            case CollectionMethod.CARD:
                return PaystackChannel.CARD

            case CollectionMethod.BANK_TRANSFER:
                return PaystackChannel.BANK_TRANSFER

            case CollectionMethod.MOBILE_MONEY:
                return PaystackChannel.MOBILE_MONEY

            case CollectionMethod.USSD:
                return PaystackChannel.USSD

            case CollectionMethod.QR:
                return PaystackChannel.QR

    @staticmethod
    def _get_recipient_type(
        request: DisbursementRequest,
    ) -> PaystackRecipientType:
        if request.method == DisbursementMethod.MOBILE_MONEY:
            return PaystackRecipientType.MOBILE_MONEY

        if request.method == DisbursementMethod.DEBIT_CARD:
            raise ValueError(
                "Paystack debit card disbursement is not supported by this integration"
            )

        match request.country:
            case Country.GHANA:
                return PaystackRecipientType.GHIPSS

            case Country.NIGERIA:
                return PaystackRecipientType.NUBAN

            case Country.SOUTH_AFRICA:
                return PaystackRecipientType.BASA

            case _:
                raise ValueError(
                    f"Paystack does not support {request.country.value} disbursements"
                )

    @staticmethod
    def _map_status(
        status: str,
    ) -> PaymentStatus:
        match status.lower():
            case "success":
                return PaymentStatus.SUCCESS

            case "failed" | "abandoned" | "reversed":
                return PaymentStatus.FAILED

            case _:
                return PaymentStatus.PENDING
