from .contracts import PaymentProvider
from .enums import Country, PaymentProvider as Provider


class PaymentProviderFactory:
    def __init__(self, providers: dict[Provider, PaymentProvider]):
        self._providers = providers

    def get_provider(
        self, country: Country, provider: Provider | None = None
    ) -> PaymentProvider:
        provider = provider or self._get_default_provider(country)
        try:
            return self._providers[provider]
        except KeyError as error:
            raise ValueError(f"Provider {provider.value!r} was not generated") from error

    def _get_default_provider(self, country: Country) -> Provider:
        routes = {
            Country.GHANA: Provider.PAYSTACK,
            Country.SOUTH_AFRICA: Provider.PAYSTACK,
            Country.NIGERIA: Provider.BACH,
            Country.UNITED_STATES: Provider.STRIPE,
            Country.CANADA: Provider.STRIPE,
        }
        try:
            return routes[country]
        except KeyError as error:
            raise ValueError(
                f"No generated provider is configured for country {country}"
            ) from error
