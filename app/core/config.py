from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "RailSwitch"
    environment: str = "development"
    database_url: str = "sqlite+aiosqlite:///./railswitch.db"
    paystack_gh_secret_key: str | None = None
    paystack_za_secret_key: str | None = None
    paystack_callback_url: str = ""
    bach_api_key: str | None = None
    bach_base_url: str = "https://sandbox-api.bachs.io"
    stripe_secret_key: str | None = None
    stripe_success_url: str = ""
    stripe_cancel_url: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
