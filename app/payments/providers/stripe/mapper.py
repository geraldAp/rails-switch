from ...contracts import (
    CheckoutRequest,
    CheckoutResponse,
    VerificationResponse,
)
from ...enums import (
    CollectionMethod,
    Currency,
    PaymentProvider,
    PaymentStatus,
)
from .types import (
    StripeCheckoutRequest,
    StripeCheckoutSession,
    StripePaymentIntent,
    StripePayout,
)


class StripeMapper:
    @staticmethod
    def to_checkout_request(
        request: CheckoutRequest, success_url: str, cancel_url: str
    ) -> StripeCheckoutRequest:
        payload: StripeCheckoutRequest = {
            "mode": "payment",
            "customer_email": request.email,
            "success_url": success_url,
            "cancel_url": cancel_url,
            "line_items": [
                {
                    "price_data": {
                        "currency": request.currency.value.lower(),
                        "unit_amount": request.amount_minor,
                        "product_data": {"name": "RailSwitch payment"},
                    },
                    "quantity": 1,
                }
            ],
        }
        if request.payment_methods:
            payload["payment_method_types"] = [
                StripeMapper._map_method(method) for method in request.payment_methods
            ]
        if request.reference is not None:
            payload["client_reference_id"] = request.reference
        if request.metadata is not None:
            payload["metadata"] = request.metadata
        return payload

    @staticmethod
    def from_checkout(
        response: StripeCheckoutSession, request: CheckoutRequest
    ) -> CheckoutResponse:
        return CheckoutResponse(
            request.reference,
            response["id"],
            PaymentProvider.STRIPE,
            PaymentStatus.PENDING,
            response["url"],
            request.payment_methods,
            request.metadata,
            dict(response),
        )

    @staticmethod
    def from_collection(
        response: StripeCheckoutSession,
        payment_intent: StripePaymentIntent | None = None,
    ) -> VerificationResponse:
        status = StripeMapper._collection_status(
            payment_intent["status"] if payment_intent else response["payment_status"]
        )
        amount = (
            payment_intent["amount"] if payment_intent else response["amount_total"]
        )
        currency = (
            payment_intent["currency"] if payment_intent else response["currency"]
        )
        raw_response: dict[str, object] = {"checkout_session": dict(response)}
        if payment_intent is not None:
            raw_response["payment_intent"] = dict(payment_intent)
        return VerificationResponse(
            response["id"],
            PaymentProvider.STRIPE,
            status,
            amount,
            Currency(currency.upper()) if currency else None,
            raw_response,
        )

    @staticmethod
    def from_payout(response: StripePayout) -> VerificationResponse:
        return VerificationResponse(
            response["id"],
            PaymentProvider.STRIPE,
            StripeMapper._payout_status(response["status"]),
            response["amount"],
            Currency(response["currency"].upper()),
            dict(response),
        )

    @staticmethod
    def _map_method(method: CollectionMethod) -> str:
        if method is CollectionMethod.CARD:
            return "card"
        if method is CollectionMethod.BANK_TRANSFER:
            return "us_bank_account"
        raise ValueError(f"Stripe does not support {method.value} checkout")

    @staticmethod
    def _collection_status(status: str) -> PaymentStatus:
        if status == "succeeded" or status == "paid":
            return PaymentStatus.SUCCESS
        if status in {"canceled", "requires_payment_method"}:
            return PaymentStatus.FAILED
        return PaymentStatus.PENDING

    @staticmethod
    def _payout_status(status: str) -> PaymentStatus:
        if status == "paid":
            return PaymentStatus.SUCCESS
        if status in {"failed", "canceled"}:
            return PaymentStatus.FAILED
        return PaymentStatus.PENDING
