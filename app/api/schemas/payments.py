from pydantic import BaseModel, EmailStr

from app.payments.enums import CollectionMethod, Country, Currency


class CheckoutRequestBody(BaseModel):
    country: Country
    amount_minor: int
    currency: Currency
    email: EmailStr
    payment_methods: list[CollectionMethod] | None = None
    
    

class CheckoutResponseBody(BaseModel):
    checkout_url: str    