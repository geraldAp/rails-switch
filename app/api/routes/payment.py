# app/api/routes/payments.py

from typing import Annotated

from fastapi import APIRouter, Depends

from app.payments.contracts import CheckoutRequest, CheckoutResponse
from app.payments.dependencies import get_payment_service
from app.payments.service import PaymentService


router = APIRouter(
    prefix="/payments",
    tags=["payments"],
)


@router.post("/checkout")
async def checkout(
    request: CheckoutRequest,
    payment_service: Annotated[
        PaymentService,
        Depends(get_payment_service),
    ],
) -> CheckoutResponse:
    return await payment_service.collect(request)