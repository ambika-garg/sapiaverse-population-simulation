"""LLM client — OpenAI-compatible chat-completions dialect.

Works with any provider that speaks the OpenAI API:
  Ollama:   base_url=http://localhost:11434/v1, api_key=ollama
  Gemini:   base_url=https://generativelanguage.googleapis.com/v1beta/openai
  Cerebras, Groq, Together, OpenRouter: base_url + key from .env
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

CACHE_DIR = Path("data/llm_cache")
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai"
DEFAULT_MAX_TOKENS = 8192
# Set to 0.0 for local providers (Ollama). Set to e.g. 5.0 for hosted free tiers.
MIN_CALL_INTERVAL = 0.0
JSON_OBJECT_PATTERN = re.compile(r"\{.*\}", re.DOTALL)


class LLMError(RuntimeError):
    """Raised when the provider returns a response we cannot use."""


class RateLimitError(LLMError):
    """Raised on 429 — caller should back off before retrying."""


def parse_json_object(text: str) -> dict[str, Any]:
    """Parse a JSON object out of model text, tolerating fences and prose."""
    cleaned = text.strip()
    cleaned = cleaned.removeprefix("```json").removeprefix("```").removesuffix("```")
    cleaned = cleaned.strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = JSON_OBJECT_PATTERN.search(cleaned)
        if not match:
            raise LLMError(f"No JSON object in response: {text[:200]}") from None
        return json.loads(match.group(0))


@dataclass
class UsageLedger:
    """Running token and call totals for one process."""

    calls: int = 0
    cache_hits: int = 0
    input_tokens: int = 0
    output_tokens: int = 0

    def summary(self) -> str:
        return (
            f"{self.calls} live calls, {self.cache_hits} cache hits, "
            f"{self.input_tokens:,} in / {self.output_tokens:,} out tokens"
        )


@dataclass
class LLMClient:
    """Async client that always returns parsed JSON objects."""

    model: str
    api_key: str
    base_url: str
    temperature: float = 0.7
    max_concurrency: int = 3
    cache_dir: Path = CACHE_DIR
    timeout: float = 600.0
    usage: UsageLedger = field(default_factory=UsageLedger)

    def __post_init__(self) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._semaphore = asyncio.Semaphore(self.max_concurrency)
        self._rate_lock = asyncio.Lock()
        self._last_request_at = 0.0

    def _cache_path(self, system: str, user: str) -> Path:
        digest = hashlib.sha256(
            f"{self.model}|{self.temperature}|{system}|{user}".encode()
        ).hexdigest()[:32]
        return self.cache_dir / f"{digest}.json"

    def _payload(self, system: str, user: str) -> dict[str, Any]:
        return {
            "model": self.model,
            "max_tokens": DEFAULT_MAX_TOKENS,
            "temperature": self.temperature,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }

    def _extract(self, payload: dict[str, Any]) -> tuple[str, int, int]:
        """Pull text and token counts out of the response."""
        try:
            text = payload["choices"][0]["message"]["content"]
            usage = payload.get("usage", {})
            return text, usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0)
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError(f"Unexpected response shape: {str(payload)[:200]}") from exc

    async def _throttle(self) -> None:
        """Space out request starts so we stay under the provider's RPM limit."""
        async with self._rate_lock:
            wait = MIN_CALL_INTERVAL - (time.monotonic() - self._last_request_at)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_request_at = time.monotonic()

    async def complete_json(self, system: str, user: str) -> dict[str, Any]:
        """Return the model's response parsed as a JSON object."""
        cache_path = self._cache_path(system, user)
        if cache_path.exists():
            self.usage.cache_hits += 1
            return json.loads(cache_path.read_text())

        async with self._semaphore:
            await self._throttle()
            async with httpx.AsyncClient(timeout=self.timeout) as http:
                response = await http.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "content-type": "application/json",
                    },
                    json=self._payload(system, user),
                )
            # Post-request sleep keeps us under burst limits even on cache misses.
            await asyncio.sleep(MIN_CALL_INTERVAL)

        if response.status_code == 429:
            raise RateLimitError(f"429: {response.text[:300]}")
        if response.status_code != httpx.codes.OK:
            raise LLMError(f"{response.status_code}: {response.text[:300]}")

        text, tokens_in, tokens_out = self._extract(response.json())
        self.usage.calls += 1
        self.usage.input_tokens += tokens_in
        self.usage.output_tokens += tokens_out

        parsed = parse_json_object(text)
        cache_path.write_text(json.dumps(parsed))
        return parsed
