from app.payments.contracts import PaymentProvider
from app.payments.enums import Country


class PaymentProviderFactory:
    def __init__(
        self,
        paystack: PaymentProvider,
        bach: PaymentProvider,
    ):
        self.paystack = paystack
        self.bach = bach

    def get_provider(self, country: Country) -> PaymentProvider:
        match country:
            case Country.GHANA | Country.SOUTH_AFRICA:
                return self.paystack

            case Country.NIGERIA:
                return self.bach