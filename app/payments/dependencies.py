from functools import lru_cache

from .config import settings
from .enums import Country, PaymentProvider as Provider
from .factory import PaymentProviderFactory
from .providers.paystack.client import PaystackClient
from .providers.paystack.provider import PaystackProvider
from .providers.bach.client import BachClient
from .providers.bach.provider import BachProvider
from .providers.stripe.client import StripeClient
from .providers.stripe.provider import StripeProvider
from .service import PaymentService


def build_payment_service() -> PaymentService:
    """Assemble the configured payment providers and common service."""
    providers = {}
    paystack_client = PaystackClient(secrets=_paystack_secrets())
    providers[Provider.PAYSTACK] = PaystackProvider(
        client=paystack_client,
        callback_url=settings.paystack_callback_url,
    )
    bach_client = BachClient(api_key=_bach_api_key(), base_url=settings.bach_base_url)
    providers[Provider.BACH] = BachProvider(client=bach_client)
    providers[Provider.STRIPE] = StripeProvider(
        StripeClient(_stripe_secret_key()),
        settings.stripe_success_url,
        settings.stripe_cancel_url,
    )
    return PaymentService(provider_factory=PaymentProviderFactory(providers))


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
            "Missing Paystack secret configuration for: "
            + ", ".join(missing_countries)
        )

    return {country: secret for country, secret in secrets.items() if secret is not None}


def _bach_api_key() -> str:
    if settings.bach_api_key is None:
        raise ValueError("Missing Bachs API key configuration")
    return settings.bach_api_key


def _stripe_secret_key() -> str:
    if settings.stripe_secret_key is None:
        raise ValueError("Missing Stripe secret key configuration")
    return settings.stripe_secret_key
