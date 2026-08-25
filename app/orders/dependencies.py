from typing import Annotated

from fastapi import Depends

from app.orders.service import OrderService
from app.payments.dependencies import get_payment_service
from app.payments.service import PaymentService


def get_order_service(
    payment_service: Annotated[PaymentService, Depends(get_payment_service)],
) -> OrderService:
    return OrderService(payment_service=payment_service)
