from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "TradeAlert"
    database_url: str = "sqlite+pysqlite:///./tradealert.db"
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "dev-secret-change-me"
    access_token_minutes: int = 60 * 24 * 7
    default_region: str = "GB"
    timezone: str = "Europe/London"
    api_public_base_url: str = "http://localhost:8000"
    mobile_deep_link_base: str = "tradealert://"

    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_messaging_service_sid: str = ""
    twilio_from_number: str = ""
    twilio_number_pool: str = "+447700900001,+447700900002,+447700900003"

    stripe_webhook_secret: str = ""

    sumup_api_key: str = ""
    sumup_merchant_code: str = ""
    sumup_webhook_secret: str = ""

    openai_api_key: str = ""
    openai_project_id: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="TRADEALERT_", extra="ignore")

    @property
    def twilio_pool(self) -> list[str]:
        return [number.strip() for number in self.twilio_number_pool.split(",") if number.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

