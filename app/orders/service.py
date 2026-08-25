from dataclasses import dataclass

from app.payments.contracts import CheckoutRequest
from app.payments.enums import (
    CollectionMethod,
    Country,
    Currency,
    PaymentProvider,
    PaymentStatus,
)
from app.payments.service import PaymentService


@dataclass(slots=True)
class OrderCheckoutResult:
    order_id: str
    reference: str | None
    provider_reference: str
    provider: PaymentProvider
    status: PaymentStatus
    checkout_url: str


class OrderService:
    def __init__(self, payment_service: PaymentService):
        self.payment_service = payment_service

    async def checkout(
        self,
        order_id: str,
        country: Country,
        currency: Currency,
        amount_minor: int,
        email: str,
        customer_name: str | None = None,
        payment_methods: list[CollectionMethod] | None = None,
        provider: PaymentProvider | None = None,
    ) -> OrderCheckoutResult:
        request = CheckoutRequest(
            country=country,
            amount_minor=amount_minor,
            currency=currency,
            email=email,
            customer_name=customer_name,
            payment_methods=payment_methods,
            provider=provider,
            reference=order_id,
            metadata={"order_id": order_id},
        )
        response = await self.payment_service.collect(request)
        return OrderCheckoutResult(
            order_id=order_id,
            reference=response.reference,
            provider_reference=response.provider_reference,
            provider=response.provider,
            status=response.status,
            checkout_url=response.checkout_url,
        )
