from typing import Annotated

from fastapi import Depends

from ..payments.dependencies import get_payment_service
from ..payments.service import PaymentService
from .service import OrderService


def get_order_service(
    payment_service: Annotated[PaymentService, Depends(get_payment_service)],
) -> OrderService:
    return OrderService(payment_service=payment_service)
