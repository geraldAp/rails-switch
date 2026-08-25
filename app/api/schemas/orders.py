from pydantic import BaseModel, EmailStr

from app.payments.enums import (
    CollectionMethod,
    Country,
    Currency,
    PaymentProvider,
    PaymentStatus,
)


class OrderCheckoutRequest(BaseModel):
    country: Country
    currency: Currency
    amount_minor: int
    email: EmailStr
    customer_name: str | None = None
    payment_methods: list[CollectionMethod] | None = None


class OrderCheckoutResponse(BaseModel):
    order_id: str
    reference: str | None
    status: PaymentStatus
    checkout_url: str
