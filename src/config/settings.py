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
    llm_model: str = Field(..., description="Model identifier")
    llm_api_key: str = Field(..., description="Provider API key")
    llm_base_url: str = Field(..., description="OpenAI-compatible base URL")
    llm_temperature: float = Field(default=0.7)
    llm_max_concurrency: int = Field(default=3)


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (one load per process)."""
    return Settings()
