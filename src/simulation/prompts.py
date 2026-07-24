"""Prompt construction.

HUMAN-OWNED ZONE. This file decides how demographic and personality context
reaches the model, and is therefore the single biggest lever on results.
Read and tune it yourself before trusting any output.
"""

from personas.models import Persona
from scenarios.registry import Scenario

VOTE_SYSTEM = (
    "You are simulating one specific San Francisco resident voting on a local "
    "ballot measure. Stay strictly in character. Reason from this person's own "
    "circumstances - their income, job, neighbourhood, housing and temperament "
    "- not from general policy analysis.\n\n"
    "You MUST pick Yes or No. Never abstain, never hedge.\n\n"
    'Reply with JSON only: {"vote": "Yes" or "No", "reason": "one sentence"}'
)

REFLECT_SYSTEM = (
    "You are the same San Francisco resident, thinking back on how you just "
    "voted. Write one sentence, in your own voice, about why you voted that way.\n\n"
    "Then judge your own conviction: did reflecting leave you FIRMER in the way "
    "you voted, or SOFTER toward the opposite side?\n"
    'Set conviction to exactly one of: "firmer", "softer", "unchanged".\n'
    'Set strength to "slight" or "strong".\n\n'
    'Reply with JSON only: {"reflection": "one sentence", '
    '"conviction": "firmer|softer|unchanged", "strength": "slight|strong"}'
)


def _trait_line(persona: Persona) -> str:
    band = persona.ocean.band
    return (
        f"openness {band(persona.ocean.openness)}, "
        f"conscientiousness {band(persona.ocean.conscientiousness)}, "
        f"extraversion {band(persona.ocean.extraversion)}, "
        f"agreeableness {band(persona.ocean.agreeableness)}, "
        f"emotional volatility {band(persona.ocean.neuroticism)}"
    )


def describe_persona(persona: Persona) -> str:
    """Render a persona as the natural-language identity block for a prompt."""
    return (
        f"You are {persona.name}, {persona.age}, living in "
        f"{persona.neighborhood}, San Francisco.\n"
        f"Ethnicity: {persona.ethnicity}\n"
        f"Work: {persona.occupation}\n"
        f"Education: {persona.education}\n"
        f"Your income: ${persona.personal_income:,}; "
        f"household income ${persona.household_income:,}\n"
        f"Housing: {persona.housing}\n"
        f"Temperament: {_trait_line(persona)}"
    )


def _stance_line(stance: float) -> str:
    if stance > 0.05:
        return f"\nYou currently lean IN FAVOUR of capping fees (stance {stance:+.2f})."
    if stance < -0.05:
        return f"\nYou currently lean AGAINST capping fees (stance {stance:+.2f})."
    return ""


def build_vote_prompt(
    persona: Persona,
    scenario: Scenario,
    stance: float = 0.0,
    reflection: str | None = None,
) -> tuple[str, str]:
    """Return (system, user) for a vote."""
    parts = [describe_persona(persona)]
    if reflection:
        parts.append(f'\nSomething you concluded recently: "{reflection}"')
    parts.append(_stance_line(stance))
    parts.append(f"\n\nQuestion: {scenario.question}")
    if scenario.incentive:
        parts.append(f"\n{scenario.incentive}")
    return VOTE_SYSTEM, "".join(parts)


def build_reflection_prompt(persona: Persona, vote: str, reason: str) -> tuple[str, str]:
    """Return (system, user) for a post-vote reflection."""
    user = (
        f"{describe_persona(persona)}\n\n"
        f"You voted {vote} on capping delivery app fees at 15%.\n"
        f'Your reason at the time: "{reason}"'
    )
    return REFLECT_SYSTEM, user
