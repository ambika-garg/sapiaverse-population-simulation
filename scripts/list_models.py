"""List the models a provider actually offers.

Usage:
    uv run python scripts/list_models.py           # uses whatever is in .env
    uv run python scripts/list_models.py gemini    # queries Gemini directly
    uv run python scripts/list_models.py cerebras  # queries Cerebras directly
"""

import os
import sys

import httpx

from config.settings import get_settings

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai"
CEREBRAS_BASE_URL = "https://api.cerebras.ai/v1"

PROVIDER_ALIASES = {
    "gemini": "gemini",
    "google": "gemini",
    "cerebras": "cerebras",
    "openai": "cerebras",
}


def list_gemini(api_key: str) -> None:
    """Gemini supports the OpenAI /models endpoint natively."""
    response = httpx.get(
        f"{GEMINI_BASE_URL}/models",
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=30.0,
    )
    response.raise_for_status()
    for entry in response.json().get("data", []):
        print(entry.get("id"))


def list_cerebras(api_key: str) -> None:
    response = httpx.get(
        f"{CEREBRAS_BASE_URL}/models",
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=30.0,
    )
    response.raise_for_status()
    for entry in response.json().get("data", []):
        print(entry.get("id"))


def main() -> None:
    settings = get_settings()
    target = sys.argv[1].lower() if len(sys.argv) > 1 else None
    provider = PROVIDER_ALIASES.get(target or settings.llm_provider.lower(), "active")

    gemini_key = os.environ.get("GEMINI_API_KEY", "")
    cerebras_key = os.environ.get("CEREBRAS_API_KEY", "")

    if provider == "gemini":
        key = gemini_key if target else settings.llm_api_key
        print(f"--- Gemini models ({GEMINI_BASE_URL}) ---")
        list_gemini(key)
    elif provider == "cerebras":
        key = cerebras_key if target else settings.llm_api_key
        print(f"--- Cerebras models ({CEREBRAS_BASE_URL}) ---")
        list_cerebras(key)
    else:
        # Fall back to whatever base_url is active in .env
        print(f"--- Models from {settings.llm_base_url} ---")
        response = httpx.get(
            f"{settings.llm_base_url}/models",
            headers={"Authorization": f"Bearer {settings.llm_api_key}"},
            timeout=30.0,
        )
        response.raise_for_status()
        for entry in response.json().get("data", []):
            print(entry.get("id"))


if __name__ == "__main__":
    main()
