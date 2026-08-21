from app.payments.contracts import PaymentProvider
from app.payments.enums import (
    Country,
)
from app.payments.enums import (
    PaymentProvider as Provider,
)


class PaymentProviderFactory:
    def __init__(
        self,
        paystack: PaymentProvider,
        bach: PaymentProvider,
    ):
        self.paystack = paystack
        self.bach = bach

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

            case _:
                raise ValueError(f"No default provider is configured for {country}")
