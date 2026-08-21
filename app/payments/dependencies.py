from app.core.config import settings
from app.payments.enums import Country
from app.payments.factory import PaymentProviderFactory
from app.payments.providers.bach.client import BachClient
from app.payments.providers.bach.provider import BachProvider
from app.payments.providers.paystack.client import PaystackClient
from app.payments.providers.paystack.provider import PaystackProvider
from app.payments.service import PaymentService
from functools import lru_cache

def build_payment_service() -> PaymentService:
    """Assemble the configured payment providers and common service."""
    paystack_client = PaystackClient(
        secrets=_paystack_secrets(),
    )
    paystack_provider = PaystackProvider(
        client=paystack_client,
        callback_url=settings.paystack_callback_url,
    )
    bach_client = BachClient(
        api_key=_bach_api_key(),
        base_url=settings.bach_base_url,
    )
    bach_provider = BachProvider(client=bach_client)
    provider_factory = PaymentProviderFactory(
        paystack=paystack_provider,
        bach=bach_provider,
    )

    return PaymentService(provider_factory=provider_factory)


@lru_cache
def get_payment_service() -> PaymentService:
    return build_payment_service()


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


def _bach_api_key() -> str:
    if settings.bach_api_key is None:
        raise ValueError("Missing Bachs API key configuration")
    return settings.bach_api_key


