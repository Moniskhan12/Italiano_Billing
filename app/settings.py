from __future__ import annotations

from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Глобальные настройки приложения."""

    app_name: str = Field(default="Italiano Billing")
    env: str = Field(default="dev")
    host: str = Field(default="localhost")
    port: int = Field(default=8000)

    # db
    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/italiano"
    )

    # JWT
    jwt_secret: SecretStr = Field(default=SecretStr("dev_secret_change_me"))
    jwt_algorithm: str = Field(default="HS256")
    access_ttl_minutes: int = Field(default=15)
    refresh_ttl_days: int = Field(default=7)
    payments_webhook_secret: SecretStr = SecretStr("mock-webhook-secret")
    renewal_days_before: int = 3
    renewal_check_interval_seconds: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
