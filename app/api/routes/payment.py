# app/api/routes/payments.py

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.schemas.payments import CheckoutRequestBody
from app.payments.contracts import CheckoutRequest, CheckoutResponse
from app.payments.dependencies import get_payment_service
from app.payments.service import PaymentService


router = APIRouter(
    prefix="/payments",
    tags=["payments"],
)


@router.post("/checkout")
async def checkout(
    body: CheckoutRequestBody,
    payment_service: Annotated[
        PaymentService,
        Depends(get_payment_service),
    ],
) -> CheckoutResponse:
    request = CheckoutRequest(
        country=body.country,
        amount_minor=body.amount_minor,
        currency=body.currency,
        email=str(body.email),
        payment_methods=body.payment_methods,
    )

    return await payment_service.collect(request)