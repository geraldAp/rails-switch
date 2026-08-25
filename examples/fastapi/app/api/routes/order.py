from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from ...orders.dependencies import get_order_service
from ...orders.service import OrderService
from ..schemas.orders import OrderCheckoutRequest, OrderCheckoutResponse

router = APIRouter(
    prefix="/orders",
    tags=["orders"],
)


@router.post("/{order_id}/checkout", response_model=OrderCheckoutResponse)
async def checkout(
    order_id: str,
    body: OrderCheckoutRequest,
    order_service: Annotated[OrderService, Depends(get_order_service)],
) -> OrderCheckoutResponse:
    try:
        result = await order_service.checkout(
            order_id=order_id,
            country=body.country,
            currency=body.currency,
            amount_minor=body.amount_minor,
            email=str(body.email),
            customer_name=body.customer_name,
            payment_methods=body.payment_methods,
            provider=body.provider,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return OrderCheckoutResponse(
        order_id=result.order_id,
        reference=result.reference,
        status=result.status,
        checkout_url=result.checkout_url,
    )
