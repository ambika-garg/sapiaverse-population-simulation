"""The agent runtime: one persona, one question, one validated decision.

Stateless by design - a pure function around an LLM call, which makes it
parallelisable and testable with a fake client.
"""

import logging

from llm.client import LLMError
from personas.models import MAX_STANCE_DELTA, Persona, Reflection, Vote
from scenarios.registry import Scenario
from simulation.prompts import build_reflection_prompt, build_vote_prompt

logger = logging.getLogger(__name__)

VALID_VOTES = {"yes": "Yes", "no": "No"}


def _normalise_vote(raw: object) -> str:
    """Coerce the model's vote into the exact literal our schema allows."""
    text = str(raw).strip().lower().rstrip(".")
    if text not in VALID_VOTES:
        raise LLMError(f"Unusable vote value: {raw!r}")
    return VALID_VOTES[text]


async def decide(
    client,
    persona: Persona,
    scenario: Scenario,
    stance: float = 0.0,
    reflection: str | None = None,
) -> Vote:
    """Ask one agent to vote, returning a validated Vote."""
    system, user = build_vote_prompt(persona, scenario, stance, reflection)
    payload = await client.complete_json(system, user)
    return Vote(
        agent_id=persona.agent_id,
        vote=_normalise_vote(payload.get("vote")),
        reason=str(payload.get("reason", "")).strip()[:500],
        stance_at_vote=stance,
    )


async def reflect(client, persona: Persona, vote: Vote) -> Reflection:
    """Ask one agent to reflect on the vote it just cast."""
    system, user = build_reflection_prompt(persona, vote.vote, vote.reason)
    payload = await client.complete_json(system, user)

    try:
        delta = float(payload.get("stance_delta", 0.0))
    except (TypeError, ValueError):
        delta = 0.0

    # The model proposes; we bound. Stance can never run away.
    delta = max(-MAX_STANCE_DELTA, min(MAX_STANCE_DELTA, delta))

    return Reflection(
        agent_id=persona.agent_id,
        text=str(payload.get("reflection", "")).strip()[:500],
        stance_delta=delta,
    )
