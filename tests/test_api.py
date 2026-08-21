from fastapi.testclient import TestClient

from app.main import app
from app.payments.contracts import CheckoutRequest, CheckoutResponse
from app.payments.dependencies import get_payment_service
from app.payments.enums import PaymentProvider, PaymentStatus


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
                "payment_methods": ["card"],
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert service.request is not None
    assert service.request.amount_minor == 5000
    assert response.json()["provider_reference"] == "provider-reference"
