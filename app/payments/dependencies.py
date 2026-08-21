from app.core.config import settings
from app.payments.contracts import PaymentProvider
from app.payments.enums import Country
from app.payments.factory import PaymentProviderFactory
from app.payments.providers.paystack.client import PaystackClient
from app.payments.providers.paystack.provider import PaystackProvider
from app.payments.service import PaymentService


def build_payment_service(bach: PaymentProvider) -> PaymentService:
    """Assemble the shared Paystack payment flow with a Bach provider."""
    paystack_client = PaystackClient(
        secrets=_paystack_secrets(),
    )
    paystack_provider = PaystackProvider(
        client=paystack_client,
        callback_url=settings.paystack_callback_url,
    )
    provider_factory = PaymentProviderFactory(
        paystack=paystack_provider,
        bach=bach,
    )

    return PaymentService(provider_factory=provider_factory)


def _paystack_secrets() -> dict[Country, str]:
    secrets = {
        Country.GHANA: settings.paystack_gh_secret_key,
        Country.SOUTH_AFRICA: settings.paystack_za_secret_key,
    }
    missing_countries = [
        country.value for country, secret in secrets.items() if secret is None
    ]

    if missing_countries:
        raise ValueError(
            "Missing Paystack secret configuration for: " + ", ".join(missing_countries)
        )

    return {
        country: secret for country, secret in secrets.items() if secret is not None
    }
