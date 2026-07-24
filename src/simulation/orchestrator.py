"""Fan a scenario out across the whole population."""

import asyncio
import logging
from collections.abc import Sequence

from llm.client import LLMError, RateLimitError
from personas.models import Persona, Reflection, Vote
from scenarios.registry import Scenario
from simulation.runtime import decide, reflect

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 4
RETRY_BACKOFF_SECONDS = 20.0
RATE_LIMIT_BACKOFF_SECONDS = 20.0


async def _with_retry(factory, label: str):
    """Run an awaitable factory, retrying transient LLM failures.

    Rate-limit (429) errors get a longer sleep than other transient errors.
    """
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return await factory()
        except RateLimitError as exc:
            if attempt == MAX_ATTEMPTS:
                logger.error("%s hit rate limit after %d attempts: %s", label, attempt, exc)
                raise
            wait = RATE_LIMIT_BACKOFF_SECONDS * attempt
            logger.warning("%s rate-limited (attempt %d), sleeping %.0fs", label, attempt, wait)
            await asyncio.sleep(wait)
        except LLMError as exc:
            if attempt == MAX_ATTEMPTS:
                logger.error("%s failed after %d attempts: %s", label, attempt, exc)
                raise
            wait = RETRY_BACKOFF_SECONDS * attempt
            logger.warning("%s attempt %d failed, retrying in %.0fs", label, attempt, wait)
            await asyncio.sleep(wait)
    raise RuntimeError("unreachable")


async def run_scenario(
    client,
    personas: Sequence[Persona],
    scenario: Scenario,
    stances: dict[str, float] | None = None,
    reflections: dict[str, str] | None = None,
) -> list[Vote]:
    """Ask every agent to vote, one at a time to respect rate limits."""
    stances = stances or {}
    reflections = reflections or {}

    votes: list[Vote] = []
    for persona in personas:
        vote = await _with_retry(
            lambda p=persona: decide(
                client,
                p,
                scenario,
                stance=stances.get(p.agent_id, 0.0),
                reflection=reflections.get(p.agent_id),
            ),
            label=f"vote[{persona.agent_id}]",
        )
        votes.append(vote)

    logger.info("Scenario %s: %d votes", scenario.scenario_id, len(votes))
    return votes


async def run_reflections(
    client, personas: Sequence[Persona], votes: Sequence[Vote]
) -> list[Reflection]:
    """Ask every agent to reflect on its vote, one at a time."""
    by_id = {p.agent_id: p for p in personas}

    results: list[Reflection] = []
    for vote in votes:
        if vote.agent_id not in by_id:
            continue
        result = await _with_retry(
            lambda v=vote: reflect(client, by_id[v.agent_id], v),
            label=f"reflect[{vote.agent_id}]",
        )
        results.append(result)

    logger.info("Collected %d reflections", len(results))
    return results
