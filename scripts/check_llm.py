"""Smoke test: can we reach the model and get valid JSON back?"""

import asyncio
import sys

from config.settings import get_settings
from llm.client import LLMClient


async def main() -> None:
    settings = get_settings()
    model = sys.argv[1] if len(sys.argv) > 1 else settings.llm_model
    client = LLMClient(
        model=model,
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
    )
    print(f"Model: {model}")

    payload = await client.complete_json(
        system='Reply with JSON only: {"vote": "Yes" or "No", "reason": "one sentence"}',
        user="You are a 54-year-old restaurant owner in the Mission, San Francisco. "
        "Would you vote Yes or No on capping delivery app fees at 15%?",
    )

    print("Response:", payload)
    print("Usage:", client.usage.summary())

    assert payload.get("vote") in {"Yes", "No"}, f"Unexpected vote: {payload}"
    print("\nOK — provider reachable, JSON parses, vote is binary.")


if __name__ == "__main__":
    asyncio.run(main())
