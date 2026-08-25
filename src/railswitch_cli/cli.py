import argparse
import shutil
import subprocess
import tomllib
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


@dataclass(frozen=True)
class ProviderCountryDefinition:
    """Country-specific configuration and routing for a provider."""

    code: str
    enum_name: str
    display_name: str
    environment_variables: tuple[str, ...] = ()
    config_fields: tuple[str, ...] = ()
    credential_setting: str | None = None


@dataclass(frozen=True)
class ProviderDefinition:
    """Everything the scaffolder needs to generate one payment provider."""

    name: str
    display_name: str
    provider_enum: str
    country_capabilities: tuple[ProviderCountryDefinition, ...]
    shared_environment_variables: tuple[str, ...]
    shared_config_fields: tuple[str, ...]
    dependency_imports: tuple[str, ...]
    service_construction: tuple[str, ...]
    helper_functions: tuple[str, ...] = ()
    country_credentials_helper_name: str | None = None
    country_credentials_label: str | None = None


@dataclass(frozen=True)
class SelectedProviderDefinition:
    """A provider plus the country capabilities selected for one scaffold."""

    provider: ProviderDefinition
    countries: tuple[ProviderCountryDefinition, ...]


PROVIDERS = (
    ProviderDefinition(
        name="paystack",
        display_name="Paystack",
        provider_enum="PAYSTACK",
        country_capabilities=(
            ProviderCountryDefinition(
                code="GH",
                enum_name="GHANA",
                display_name="Ghana",
                environment_variables=("PAYSTACK_GH_SECRET_KEY=",),
                config_fields=("    paystack_gh_secret_key: str | None = None",),
                credential_setting="paystack_gh_secret_key",
            ),
            ProviderCountryDefinition(
                code="ZA",
                enum_name="SOUTH_AFRICA",
                display_name="South Africa",
                environment_variables=("PAYSTACK_ZA_SECRET_KEY=",),
                config_fields=("    paystack_za_secret_key: str | None = None",),
                credential_setting="paystack_za_secret_key",
            ),
        ),
        shared_environment_variables=("PAYSTACK_CALLBACK_URL=",),
        shared_config_fields=(
            "    # Paystack - Ghana and South Africa",
            '    paystack_callback_url: str = ""',
        ),
        dependency_imports=(
            "from .providers.paystack.client import PaystackClient",
            "from .providers.paystack.provider import PaystackProvider",
        ),
        service_construction=(
            "    paystack_client = PaystackClient(secrets=_paystack_secrets())",
            "    providers[Provider.PAYSTACK] = PaystackProvider(",
            "        client=paystack_client,",
            "        callback_url=settings.paystack_callback_url,",
            "    )",
        ),
        country_credentials_helper_name="paystack_secrets",
        country_credentials_label="Paystack secret",
    ),
    ProviderDefinition(
        name="bach",
        display_name="Bachs",
        provider_enum="BACH",
        country_capabilities=(
            ProviderCountryDefinition(
                code="NG",
                enum_name="NIGERIA",
                display_name="Nigeria",
            ),
        ),
        shared_environment_variables=(
            "BACH_API_KEY=",
            "BACH_BASE_URL=https://sandbox-api.bachs.io",
        ),
        shared_config_fields=(
            "    # Bachs - Nigeria",
            "    bach_api_key: str | None = None",
            '    bach_base_url: str = "https://sandbox-api.bachs.io"',
        ),
        dependency_imports=(
            "from .providers.bach.client import BachClient",
            "from .providers.bach.provider import BachProvider",
        ),
        service_construction=(
            "    bach_client = BachClient(api_key=_bach_api_key(), base_url=settings.bach_base_url)",
            "    providers[Provider.BACH] = BachProvider(client=bach_client)",
        ),
        helper_functions=(
            (
                "def _bach_api_key() -> str:\n"
                "    if settings.bach_api_key is None:\n"
                '        raise ValueError("Missing Bachs API key configuration")\n'
                "    return settings.bach_api_key"
            ),
        ),
    ),
    ProviderDefinition(
        name="stripe",
        display_name="Stripe",
        provider_enum="STRIPE",
        country_capabilities=(
            ProviderCountryDefinition(
                code="US",
                enum_name="UNITED_STATES",
                display_name="United States",
            ),
            ProviderCountryDefinition(
                code="CA",
                enum_name="CANADA",
                display_name="Canada",
            ),
        ),
        shared_environment_variables=(
            "STRIPE_SECRET_KEY=",
            "STRIPE_SUCCESS_URL=",
            "STRIPE_CANCEL_URL=",
        ),
        shared_config_fields=(
            "    # Stripe - United States and Canada",
            "    stripe_secret_key: str | None = None",
            '    stripe_success_url: str = ""',
            '    stripe_cancel_url: str = ""',
        ),
        dependency_imports=(
            "from .providers.stripe.client import StripeClient",
            "from .providers.stripe.provider import StripeProvider",
        ),
        service_construction=(
            "    providers[Provider.STRIPE] = StripeProvider(",
            "        StripeClient(_stripe_secret_key()),",
            "        settings.stripe_success_url,",
            "        settings.stripe_cancel_url,",
            "    )",
        ),
        helper_functions=(
            (
                "def _stripe_secret_key() -> str:\n"
                "    if settings.stripe_secret_key is None:\n"
                '        raise ValueError("Missing Stripe secret key configuration")\n'
                "    return settings.stripe_secret_key"
            ),
        ),
    ),
)

PROVIDERS_BY_NAME = {provider.name: provider for provider in PROVIDERS}
PROVIDER_NAMES = tuple(PROVIDERS_BY_NAME)
COUNTRY_CODES = tuple(
    dict.fromkeys(
        country.code
        for provider in PROVIDERS
        for country in provider.country_capabilities
    )
)

GENERATED_RUNTIME_DEPENDENCIES = (
    "httpx2",
    "pydantic-settings",
)


class DependencyInstallStatus(StrEnum):
    INSTALLED = "installed"
    ALREADY_INSTALLED = "already_installed"
    SKIPPED = "skipped"
    FAILED = "failed"


def update_env_example(
    env_path: Path,
    providers: tuple[SelectedProviderDefinition, ...] | None = None,
) -> bool:
    """Append missing RailSwitch environment variables to env_path."""
    if providers is None:
        providers = tuple(
            SelectedProviderDefinition(provider, provider.country_capabilities)
            for provider in PROVIDERS
        )

    existing_content = env_path.read_text() if env_path.exists() else ""

    existing_variables = {
        line.split("=", maxsplit=1)[0].strip()
        for line in existing_content.splitlines()
        if "=" in line and line.split("=", maxsplit=1)[0].strip().isidentifier()
    }

    sections_to_add = []

    for selected_provider in providers:
        provider = selected_provider.provider
        variables = (
            *(
                variable
                for country in selected_provider.countries
                for variable in country.environment_variables
            ),
            *provider.shared_environment_variables,
        )
        missing_variables = [
            variable
            for variable in variables
            if variable.split("=", maxsplit=1)[0] not in existing_variables
        ]

        if missing_variables:
            sections_to_add.append(
                "\n".join(
                    (
                        "# ------------------------------------------------",
                        f"# RailSwitch - {provider.display_name}",
                        "# "
                        + ", ".join(
                            country.display_name
                            for country in selected_provider.countries
                        ),
                        "# ------------------------------------------------",
                        *missing_variables,
                    )
                )
            )

    if not sections_to_add:
        return False

    addition = "\n\n".join(sections_to_add) + "\n"

    if existing_content:
        separator = "\n" if existing_content.endswith("\n") else "\n\n"
        env_path.write_text(existing_content + separator + addition)
    else:
        env_path.write_text(addition)

    return True


def generate_selected_files(
    target_path: Path, providers: tuple[SelectedProviderDefinition, ...]
) -> None:
    """Generate the provider-sensitive modules from the selected metadata."""
    config_blocks = []
    for selected_provider in providers:
        provider = selected_provider.provider
        country_names = " and ".join(
            country.display_name for country in selected_provider.countries
        )
        comment = f"    # {provider.display_name} - {country_names}"
        non_comment_shared = tuple(
            field
            for field in provider.shared_config_fields
            if not field.lstrip().startswith("#")
        )
        country_fields = tuple(
            field
            for country in selected_provider.countries
            for field in country.config_fields
        )
        block = "\n".join((comment, *non_comment_shared, *country_fields))
        config_blocks.append(block)
    config_fields = "\n\n".join(config_blocks)
    _ = (target_path / "config.py").write_text(
        "from pydantic_settings import BaseSettings, SettingsConfigDict\n\n\n"  # pyright: ignore[reportImplicitStringConcatenation]
        "class PaymentSettings(BaseSettings):\n"
        f"{config_fields}\n\n"
        "    model_config = SettingsConfigDict(\n"
        '        env_file=".env",\n'
        '        env_file_encoding="utf-8",\n'
        '        extra="ignore",\n'
        "    )\n\n\n"
        "settings = PaymentSettings()\n"
    )

    imports = "\n".join(
        item
        for selected_provider in providers
        for item in selected_provider.provider.dependency_imports
    )
    constructions = "\n".join(
        item
        for selected_provider in providers
        for item in selected_provider.provider.service_construction
    )
    helpers = "\n\n\n".join(
        item
        for selected_provider in providers
        for item in (
            *selected_provider.provider.helper_functions,
            *_country_credentials_helper(selected_provider),
        )
    )
    _ = (target_path / "dependencies.py").write_text(
        "from functools import lru_cache\n\n"  # pyright: ignore[reportImplicitStringConcatenation]
        "from .config import settings\n"
        "from .enums import Country, PaymentProvider as Provider\n"
        "from .factory import PaymentProviderFactory\n"
        f"{imports}\n"
        "from .service import PaymentService\n\n\n"
        "def build_payment_service() -> PaymentService:\n"
        '    """Assemble the configured payment providers and common service."""\n'
        "    providers = {}\n"
        f"{constructions}\n"
        "    return PaymentService(provider_factory=PaymentProviderFactory(providers))\n\n\n"
        "@lru_cache\n"
        "def get_payment_service() -> PaymentService:\n"
        "    return build_payment_service()\n\n\n"
        f"{helpers}\n"
    )

    providers_by_country: dict[str, list[str]] = {}
    for selected_provider in providers:
        for country in selected_provider.countries:
            providers_by_country.setdefault(country.enum_name, []).append(
                selected_provider.provider.provider_enum
            )
    routes = "\n".join(
        f"    Country.{country}: {{{', '.join(f'Provider.{provider}' for provider in provider_enums)}}},"
        for country, provider_enums in providers_by_country.items()
    )
    _write_factory(target_path, routes)


def _country_credentials_helper(
    selected_provider: SelectedProviderDefinition,
) -> tuple[str, ...]:
    """Generate validation for per-country credentials when a provider needs it."""
    provider = selected_provider.provider
    if provider.country_credentials_helper_name is None:
        return ()

    credentials = tuple(
        country for country in selected_provider.countries if country.credential_setting
    )
    if not credentials:
        return ()

    secrets = "\n".join(
        f"        Country.{country.enum_name}: settings.{country.credential_setting},"
        for country in credentials
    )
    return (
        "\n".join(
            (
                f"def _{provider.country_credentials_helper_name}() -> dict[Country, str]:",
                "    secrets = {",
                secrets,
                "    }",
                "    missing_countries = [",
                "        country.value for country, secret in secrets.items() if secret is None",
                "    ]",
                "",
                "    if missing_countries:",
                "        raise ValueError(",
                f'            "Missing {provider.country_credentials_label} configuration for: "',
                '            + ", ".join(missing_countries)',
                "        )",
                "",
                "    return {country: secret for country, secret in secrets.items() if secret is not None}",
            )
        ),
    )


def _write_factory(target_path: Path, routes: str) -> None:
    (target_path / "factory.py").write_text(
        "from .contracts import PaymentProvider\n"
        "from .enums import Country, PaymentProvider as Provider\n\n\n"
        "ROUTES = {\n"
        f"{routes}\n"
        "}\n\n\n"
        "class PaymentProviderFactory:\n"
        "    def __init__(\n"
        "        self,\n"
        "        providers: dict[Provider, PaymentProvider],\n"
        "        routes: dict[Country, set[Provider]] | None = None,\n"
        "    ):\n"
        "        self._providers = providers\n\n"
        "        self._routes = ROUTES if routes is None else routes\n\n"
        "    def get_provider(\n"
        "        self, country: Country, provider: Provider | None = None\n"
        "    ) -> PaymentProvider:\n"
        "        configured_providers = self._routes.get(country)\n"
        "        if not configured_providers:\n"
        "            raise ValueError(\n"
        '                f"No generated provider is configured for country {country.value}"\n'
        "            )\n\n"
        "        if provider is not None:\n"
        "            if provider not in configured_providers:\n"
        "                raise ValueError(\n"
        '                    f"Provider {provider.value!r} is not configured for country "\n'
        '                    f"{country.value}"\n'
        "                )\n"
        "            return self._get_generated_provider(provider)\n\n"
        "        if len(configured_providers) > 1:\n"
        "            raise ValueError(\n"
        '                f"Multiple providers are configured for country {country.value}; "\n'
        '                "specify a provider"\n'
        "            )\n\n"
        "        return self._get_generated_provider(next(iter(configured_providers)))\n\n"
        "    def _get_generated_provider(self, provider: Provider) -> PaymentProvider:\n"
        "        try:\n"
        "            return self._providers[provider]\n"
        "        except KeyError as error:\n"
        '            raise ValueError(f"Provider {provider.value!r} was not generated") from error\n\n'
    )


def select_provider_capabilities(
    provider_names: tuple[str, ...], country_codes: tuple[str, ...] | None
) -> tuple[SelectedProviderDefinition, ...]:
    """Select valid provider-country capabilities while preserving CLI order."""
    providers = tuple(PROVIDERS_BY_NAME[name] for name in provider_names)
    if country_codes is None:
        return tuple(
            SelectedProviderDefinition(provider, provider.country_capabilities)
            for provider in providers
        )

    supported_codes = {
        country.code
        for provider in providers
        for country in provider.country_capabilities
    }
    unsupported_codes = [code for code in country_codes if code not in supported_codes]
    if unsupported_codes:
        raise ValueError(
            "Selected providers do not support countries: "
            + ", ".join(unsupported_codes)
        )

    selected = []
    for provider in providers:
        countries_by_code = {
            country.code: country for country in provider.country_capabilities
        }
        countries = tuple(
            countries_by_code[code]
            for code in country_codes
            if code in countries_by_code
        )
        if not countries:
            raise ValueError(
                f"Provider {provider.name!r} does not support the selected countries"
            )
        selected.append(SelectedProviderDefinition(provider, countries))

    return tuple(selected)


def install_generated_dependencies(
    project_root: Path,
) -> DependencyInstallStatus:
    pyproject_path = project_root / "pyproject.toml"

    if not pyproject_path.exists():
        return DependencyInstallStatus.SKIPPED

    with pyproject_path.open("rb") as file:
        pyproject = tomllib.load(file)

    project_dependencies = pyproject.get("project", {}).get("dependencies", [])

    all_installed = all(
        any(dependency.startswith(name) for dependency in project_dependencies)
        for name in GENERATED_RUNTIME_DEPENDENCIES
    )

    if all_installed:
        return DependencyInstallStatus.ALREADY_INSTALLED

    uv_path = shutil.which("uv")

    if uv_path is None:
        return DependencyInstallStatus.SKIPPED

    try:
        subprocess.run(
            [
                uv_path,
                "add",
                *GENERATED_RUNTIME_DEPENDENCIES,
            ],
            cwd=project_root,
            check=True,
        )
    except subprocess.CalledProcessError:
        return DependencyInstallStatus.FAILED

    return DependencyInstallStatus.INSTALLED


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="railswitch",
        description="RailSwitch payment scaffolding CLI",
    )

    subparsers = parser.add_subparsers(dest="command")

    init_parser = subparsers.add_parser(
        "init",
        help="Initialize RailSwitch in a project",
    )

    init_parser.add_argument(
        "--path",
        default="app/payments",
        help="Target path for the generated RailSwitch module",
    )
    init_parser.add_argument(
        "--providers",
        nargs="+",
        choices=PROVIDER_NAMES,
        default=None,
        help="Payment providers to generate (defaults to all providers)",
    )
    init_parser.add_argument(
        "--countries",
        nargs="+",
        choices=COUNTRY_CODES,
        help="Countries to generate for the selected providers (defaults to all supported)",
    )

    args = parser.parse_args()

    if args.command == "init":
        target_path = Path(args.path)
        selected_country_codes = (
            tuple(dict.fromkeys(args.countries)) if args.countries is not None else None
        )
        if args.providers is None:
            if selected_country_codes is not None:
                country_to_provider = {
                    country.code: provider.name
                    for provider in PROVIDERS
                    for country in provider.country_capabilities
                }
                selected_provider_names = tuple(
                    dict.fromkeys(
                        country_to_provider[code] for code in selected_country_codes
                    )
                )
            else:
                selected_provider_names = PROVIDER_NAMES
        else:
            selected_provider_names = tuple(dict.fromkeys(args.providers))
        try:
            selected_providers = select_provider_capabilities(
                selected_provider_names,
                selected_country_codes,
            )
        except ValueError as error:
            init_parser.error(str(error))

        print(f"Initializing RailSwitch at: {target_path}")
        print(f"Absolute path: {target_path.resolve()}")

        if target_path.exists():
            print(f"Cannot initialize RailSwitch: {target_path} already exists.")
            return

        template_path = Path(__file__).parent / "templates" / "payments"

        shutil.copytree(
            template_path,
            target_path,
            ignore=shutil.ignore_patterns(
                "config.py",
                "dependencies.py",
                "factory.py",
                *PROVIDER_NAMES,
            ),
        )
        for provider in selected_providers:
            shutil.copytree(
                template_path / "providers" / provider.provider.name,
                target_path / "providers" / provider.provider.name,
            )
        generate_selected_files(target_path, selected_providers)

        print(f"RailSwitch initialized at: {target_path}")

        if update_env_example(Path(".env.example"), selected_providers):
            print("Updated .env.example with RailSwitch environment variables.")
        else:
            print(".env.example already contains all RailSwitch variables.")

        dependency_status = install_generated_dependencies(Path.cwd())

        match dependency_status:
            case DependencyInstallStatus.INSTALLED:
                print("Installed required RailSwitch dependencies.")

            case DependencyInstallStatus.ALREADY_INSTALLED:
                print("All required RailSwitch dependencies are already installed.")

            case DependencyInstallStatus.FAILED:
                print("RailSwitch was scaffolded, but dependency installation failed.")
                print("Run: uv add " + " ".join(GENERATED_RUNTIME_DEPENDENCIES))

            case DependencyInstallStatus.SKIPPED:
                print("\nInstall required dependencies:")
                print("  uv add " + " ".join(GENERATED_RUNTIME_DEPENDENCIES))
