"""Typed application configuration loaded from environment variables."""

from functools import lru_cache
from typing import Literal
from urllib.parse import quote_plus

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings shared across ChoreTracker components."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "ChoreTracker"
    app_env: Literal["development", "test", "staging", "production"] = "development"

    api_host: str = "127.0.0.1"
    api_port: int = Field(default=8110, ge=1, le=65535)

    frontend_port: int = Field(default=51810, ge=1, le=65535)

    postgres_db: str = "choretracker"
    postgres_user: str = "choretracker_app"
    postgres_password: str = "development-only-password"
    postgres_host: str = "127.0.0.1"
    postgres_host_port: int = Field(default=55410, ge=1, le=65535)
    postgres_container_port: int = Field(default=5432, ge=1, le=65535)

    @property
    def database_url(self) -> str:
        """Build the application PostgreSQL connection URL."""

        username = quote_plus(self.postgres_user)
        password = quote_plus(self.postgres_password)

        return (
            f"postgresql+psycopg://{username}:{password}"
            f"@{self.postgres_host}:{self.postgres_host_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    """Return one cached settings instance for the running process."""

    return Settings()
