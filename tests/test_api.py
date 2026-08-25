import asyncio

from fastapi.testclient import TestClient

from app.api.schemas.orders import OrderCheckoutResponse
from app.main import app
from app.orders.service import OrderService
from app.payments.contracts import CheckoutRequest, CheckoutResponse
from app.payments.dependencies import get_payment_service
from app.payments.enums import (
    CollectionMethod,
    Country,
    Currency,
    PaymentOperation,
    PaymentProvider,
    PaymentStatus,
)
from app.payments.errors import PaymentProviderError, ProviderErrorCategory
from app.payments.service import PaymentService


class CheckoutServiceSpy(PaymentService):
    def __init__(self) -> None:
        self.request: CheckoutRequest | None = None

    async def collect(self, request: CheckoutRequest) -> CheckoutResponse:
        self.request = request
        return CheckoutResponse(
            reference="payment-reference",
            provider_reference="provider-reference",
            provider=PaymentProvider.PAYSTACK,
            status=PaymentStatus.PENDING,
            checkout_url="https://checkout.example.test",
        )


def test_order_checkout_route_reaches_order_service() -> None:
    service = CheckoutServiceSpy()
    app.dependency_overrides[get_payment_service] = lambda: service

    try:
        response = TestClient(app).post(
            "/orders/order_123/checkout",
            json={
                "country": "GH",
                "currency": "GHS",
                "amount_minor": 5000,
                "email": "customer@example.com",
                "customer_name": "Customer Example",
                "payment_methods": ["card", "mobile_money"],
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert service.request is not None
    assert service.request.reference == "order_123"
    assert service.request.metadata == {"order_id": "order_123"}
    assert service.request.amount_minor == 5000
    assert service.request.country.value == "GH"
    data = response.json()
    assert set(data) == set(OrderCheckoutResponse.model_fields)
    assert data == {
        "order_id": "order_123",
        "reference": "payment-reference",
        "provider_reference": "provider-reference",
        "provider": "paystack",
        "status": "pending",
        "checkout_url": "https://checkout.example.test",
    }


def test_order_service_constructs_checkout_request_correctly() -> None:
    spy = CheckoutServiceSpy()
    order_service = OrderService(payment_service=spy)

    result = asyncio.run(
        order_service.checkout(
            order_id="order_999",
            country=Country.GHANA,
            currency=Currency.GHS,
            amount_minor=5000,
            email="customer@example.com",
            customer_name="Customer Example",
            payment_methods=[CollectionMethod.CARD],
        )
    )

    assert spy.request is not None
    assert spy.request.reference == "order_999"
    assert spy.request.metadata == {"order_id": "order_999"}
    assert spy.request.email == "customer@example.com"
    assert result.order_id == "order_999"
    assert result.reference == "payment-reference"
    assert result.provider_reference == "provider-reference"
    assert result.provider == PaymentProvider.PAYSTACK
    assert result.status == PaymentStatus.PENDING
    assert result.checkout_url == "https://checkout.example.test"


def test_order_checkout_returns_public_order_checkout_response() -> None:
    service = CheckoutServiceSpy()
    app.dependency_overrides[get_payment_service] = lambda: service

    try:
        response = TestClient(app).post(
            "/orders/ord_42/checkout",
            json={
                "country": "GH",
                "currency": "GHS",
                "amount_minor": 2500,
                "email": "buyer@example.com",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert set(data) == set(OrderCheckoutResponse.model_fields)
    assert data == {
        "order_id": "ord_42",
        "reference": "payment-reference",
        "provider_reference": "provider-reference",
        "provider": "paystack",
        "status": "pending",
        "checkout_url": "https://checkout.example.test",
    }


class ProviderErrorServiceSpy(PaymentService):
    def __init__(self) -> None:
        pass

    async def collect(self, _request: CheckoutRequest) -> CheckoutResponse:
        raise PaymentProviderError(
            provider=PaymentProvider.STRIPE,
            operation=PaymentOperation.COLLECTION,
            category=ProviderErrorCategory.VALIDATION,
            message="Stripe rejected the checkout request.",
            provider_code="parameter_invalid_empty",
            status_code=400,
            retryable=False,
            raw_response={"error": {"secret_detail": "not public"}},
        )


def test_order_checkout_returns_normalized_provider_error() -> None:
    app.dependency_overrides[get_payment_service] = lambda: ProviderErrorServiceSpy()

    try:
        response = TestClient(app).post(
            "/orders/order_err/checkout",
            json={
                "country": "US",
                "amount_minor": 5000,
                "currency": "USD",
                "email": "buyer@example.com",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert response.json() == {
        "detail": {
            "provider": "stripe",
            "operation": "collection",
            "category": "validation",
            "code": "parameter_invalid_empty",
            "message": "Stripe rejected the checkout request.",
            "retryable": False,
        }
    }


def test_order_checkout_propagates_value_error_as_422() -> None:
    class ValueErrorSpy(PaymentService):
        def __init__(self) -> None:
            pass

        async def collect(self, _request: CheckoutRequest) -> CheckoutResponse:
            raise ValueError("No generated provider is configured for country GH")

    app.dependency_overrides[get_payment_service] = lambda: ValueErrorSpy()

    try:
        response = TestClient(app).post(
            "/orders/order_val/checkout",
            json={
                "country": "GH",
                "currency": "GHS",
                "amount_minor": 1000,
                "email": "buyer@example.com",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert "No generated provider" in response.json()["detail"]
