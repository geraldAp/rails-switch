from app.payments.contracts import PaymentProvider
from app.payments.enums import (
    Country,
    PaymentProvider as Provider,
)


class PaymentProviderFactory:
    def __init__(
        self,
        paystack: PaymentProvider,
        bach: PaymentProvider,
    ):
        self.providers: dict[tuple[Provider, Country], PaymentProvider] = {
            (Provider.PAYSTACK, Country.GHANA): paystack,
            (Provider.PAYSTACK, Country.SOUTH_AFRICA): paystack,
            (Provider.BACH, Country.NIGERIA): bach,
        }

    def get_provider(
        self,
        country: Country,
        provider: Provider | None = None,
    ) -> PaymentProvider:
        if provider is None:
            provider = self._get_default_provider(country)

        key = (provider, country)

        if key not in self.providers:
            raise ValueError(
                f"Provider {provider} is not configured for {country}"
            )

        return self.providers[key]

    def _get_default_provider(
        self,
        country: Country,
    ) -> Provider:
        match country:
            case Country.GHANA | Country.SOUTH_AFRICA:
                return Provider.PAYSTACK

            case Country.NIGERIA:
                return Provider.BACH