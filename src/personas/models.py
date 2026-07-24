"""Core domain models for simulated residents."""

from typing import Literal

from pydantic import BaseModel, Field

HIGH_TRAIT_THRESHOLD = 0.66
LOW_TRAIT_THRESHOLD = 0.33


class OceanProfile(BaseModel):
    """Big Five personality scores, each on a 0-1 scale.

    Synthesized, not measured — see src/personas/ocean.py.
    """

    openness: float = Field(ge=0.0, le=1.0)
    conscientiousness: float = Field(ge=0.0, le=1.0)
    extraversion: float = Field(ge=0.0, le=1.0)
    agreeableness: float = Field(ge=0.0, le=1.0)
    neuroticism: float = Field(ge=0.0, le=1.0)

    @staticmethod
    def band(score: float) -> str:
        """Describe a score in words, which language models reason with better."""
        if score >= HIGH_TRAIT_THRESHOLD:
            return "high"
        if score <= LOW_TRAIT_THRESHOLD:
            return "low"
        return "moderate"


class Persona(BaseModel):
    """A single simulated San Francisco resident."""

    agent_id: str
    name: str
    age: int = Field(ge=18)
    neighborhood: str
    puma: str
    ethnicity: str
    occupation: str
    education: str
    personal_income: int
    household_income: int
    housing: str
    ocean: OceanProfile


# ---------------------------------------------------------------------------
# Stance + Vote + Reflection
# ---------------------------------------------------------------------------

STANCE_FLOOR, STANCE_CEILING = -1.0, 1.0
MAX_STANCE_DELTA = 0.25
INITIAL_STANCE = 0.0


def clamp_stance(value: float) -> float:
    """Keep a stance inside its valid range, however large the delta."""
    return max(STANCE_FLOOR, min(STANCE_CEILING, value))


class Vote(BaseModel):
    """One agent's decision in one scenario."""

    agent_id: str
    vote: Literal["Yes", "No"]
    reason: str
    stance_at_vote: float = INITIAL_STANCE


class Reflection(BaseModel):
    """A post-vote reflection and its bounded stance nudge."""

    agent_id: str
    text: str
    stance_delta: float = Field(ge=-MAX_STANCE_DELTA, le=MAX_STANCE_DELTA)
