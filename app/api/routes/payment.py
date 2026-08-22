# app/api/routes/payments.py

from typing import Annotated

import httpx2
from fastapi import APIRouter, Depends, HTTPException

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
        customer_name=body.customer_name,
        payment_methods=body.payment_methods,
    )

    try:
        return await payment_service.collect(request)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except httpx2.HTTPStatusError as error:
        try:
            detail: object = error.response.json()
        except ValueError:
            detail = error.response.text
        raise HTTPException(
            status_code=error.response.status_code,
            detail=detail,
        ) from error
