from fastapi.testclient import TestClient

from app.main import app
from app.payments.contracts import CheckoutRequest, CheckoutResponse
from app.payments.dependencies import get_payment_service
from app.payments.enums import PaymentOperation, PaymentProvider, PaymentStatus
from app.payments.errors import PaymentProviderError, ProviderErrorCategory


class CheckoutServiceSpy:
    def __init__(self) -> None:
        self.request: CheckoutRequest | None = None

    async def collect(self, request: CheckoutRequest) -> CheckoutResponse:
        self.request = request
        return CheckoutResponse(
            reference=request.reference,
            provider_reference="provider-reference",
            provider=PaymentProvider.PAYSTACK,
            status=PaymentStatus.PENDING,
            checkout_url="https://checkout.example.test",
        )


def test_payment_checkout_route_is_mounted() -> None:
    service = CheckoutServiceSpy()
    app.dependency_overrides[get_payment_service] = lambda: service

    try:
        response = TestClient(app).post(
            "/payments/checkout",
            json={
                "country": "GH",
                "amount_minor": 5000,
                "currency": "GHS",
                "email": "buyer@example.com",
                "customer_name": "Buyer Example",
                "payment_methods": ["card"],
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert service.request is not None
    assert service.request.amount_minor == 5000
    assert response.json()["provider_reference"] == "provider-reference"


class ProviderErrorServiceSpy:
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


def test_payment_checkout_returns_normalized_provider_error() -> None:
    app.dependency_overrides[get_payment_service] = lambda: ProviderErrorServiceSpy()

    try:
        response = TestClient(app).post(
            "/payments/checkout",
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
