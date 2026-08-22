from .contracts import PaymentProvider
from .enums import (
    Country,
)
from .enums import (
    PaymentProvider as Provider,
)


class PaymentProviderFactory:
    def __init__(
        self,
        paystack: PaymentProvider,
        bach: PaymentProvider,
        stripe: PaymentProvider,
    ):
        self.paystack = paystack
        self.bach = bach
        self.stripe = stripe

    def get_provider(
        self,
        country: Country,
        provider: Provider | None = None,
    ) -> PaymentProvider:
        if provider is None:
            provider = self._get_default_provider(country)

        match provider:
            case Provider.PAYSTACK:
                return self.paystack

            case Provider.BACH:
                return self.bach
            case Provider.STRIPE:
                return self.stripe

            case _:
                raise ValueError(f"Provider {provider} is not configured")

    def _get_default_provider(
        self,
        country: Country,
    ) -> Provider:
        match country:
            case Country.GHANA | Country.SOUTH_AFRICA:
                return Provider.PAYSTACK

            case Country.NIGERIA:
                return Provider.BACH
            case Country.UNITED_STATES | Country.CANADA:
                return Provider.STRIPE

            case _:
                raise ValueError(f"No default provider is configured for {country}")
