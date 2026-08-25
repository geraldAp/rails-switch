from .contracts import PaymentProvider
from .enums import Country
from .enums import PaymentProvider as Provider

ROUTES = {
    Country.GHANA: {Provider.PAYSTACK},
    Country.SOUTH_AFRICA: {Provider.PAYSTACK},
    Country.NIGERIA: {Provider.BACH},
    Country.UNITED_STATES: {Provider.STRIPE},
    Country.CANADA: {Provider.STRIPE},
}


class PaymentProviderFactory:
    def __init__(
        self,
        providers: dict[Provider, PaymentProvider],
        routes: dict[Country, set[Provider]] | None = None,
    ):
        self._providers = providers
        self._routes = ROUTES if routes is None else routes

    def get_provider(
        self, country: Country, provider: Provider | None = None
    ) -> PaymentProvider:
        configured_providers = self._routes.get(country)
        if not configured_providers:
            raise ValueError(
                f"No generated provider is configured for country {country.value}"
            )

        if provider is not None:
            if provider not in configured_providers:
                raise ValueError(
                    f"Provider {provider.value!r} is not configured for country "
                    f"{country.value}"
                )
            return self._get_generated_provider(provider)

        if len(configured_providers) > 1:
            raise ValueError(
                f"Multiple providers are configured for country {country.value}; "
                "specify a provider"
            )

        return self._get_generated_provider(next(iter(configured_providers)))

    def _get_generated_provider(self, provider: Provider) -> PaymentProvider:
        try:
            return self._providers[provider]
        except KeyError as error:
            raise ValueError(
                f"Provider {provider.value!r} was not generated"
            ) from error
