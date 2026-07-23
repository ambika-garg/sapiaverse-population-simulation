"""Application configuration loaded from environment / .env."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application settings, sourced from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    anthropic_api_key: str | None = Field(default=None, description="API key for the LLM provider")
    census_api_key: str | None = Field(default=None, description="Optional Census API key")
    log_level: str = Field(default="INFO", description="Logging verbosity")


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (one load per process)."""
    return Settings()
