"""Tests for application configuration."""

from src.config.settings import get_settings


def test_settings_loads_from_env(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.anthropic_api_key == "test-key"
    assert settings.log_level == "INFO"
