"""Turn raw votes into the outputs the challenge asks for."""

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field

from personas.models import Persona, Vote

TOP_REASONS = 3

CLUSTER_SYSTEM = (
    "You group short voter statements into themes. Reply with JSON only: "
    '{"themes": [{"theme": "short label", "count": integer}]}. '
    "Order by count descending. Use at most 5 themes."
)


@dataclass
class VoteSummary:
    """Aggregate outcome of one scenario run."""

    total: int
    yes: int
    no: int
    yes_pct: float
    yes_reasons: list[str] = field(default_factory=list)
    no_reasons: list[str] = field(default_factory=list)
    themes_yes: list[tuple[str, int]] = field(default_factory=list)
    themes_no: list[tuple[str, int]] = field(default_factory=list)


def summarise(votes: Sequence[Vote]) -> VoteSummary:
    """Compute the headline split and collect reasons per side."""
    counts = Counter(v.vote for v in votes)
    total = len(votes)
    yes = counts.get("Yes", 0)
    return VoteSummary(
        total=total,
        yes=yes,
        no=counts.get("No", 0),
        yes_pct=round(100 * yes / total, 1) if total else 0.0,
        yes_reasons=[v.reason for v in votes if v.vote == "Yes"],
        no_reasons=[v.reason for v in votes if v.vote == "No"],
    )


async def cluster_reasons(client, reasons: Sequence[str]) -> list[tuple[str, int]]:
    """Group free-text reasons into themes with one LLM call."""
    if not reasons:
        return []
    numbered = "\n".join(f"{i + 1}. {r}" for i, r in enumerate(reasons))
    payload = await client.complete_json(CLUSTER_SYSTEM, numbered)
    themes = payload.get("themes", [])
    return [(str(t.get("theme", "")).strip(), int(t.get("count", 0))) for t in themes[:TOP_REASONS]]


def segment_split(
    votes: Sequence[Vote], personas: Sequence[Persona], attribute: str
) -> dict[str, dict[str, float | int]]:
    """Yes/No split grouped by a persona attribute, with cell sizes.

    Cell sizes are reported alongside percentages because at n=30 a segment
    of four agents produces percentages that look precise and are not.
    """
    by_id = {p.agent_id: p for p in personas}
    buckets: dict[str, list[Vote]] = {}
    for vote in votes:
        persona = by_id.get(vote.agent_id)
        if persona is None:
            continue
        buckets.setdefault(str(getattr(persona, attribute)), []).append(vote)

    result = {}
    for key, group in sorted(buckets.items()):
        yes = sum(1 for v in group if v.vote == "Yes")
        result[key] = {
            "n": len(group),
            "yes": yes,
            "no": len(group) - yes,
            "yes_pct": round(100 * yes / len(group), 1),
        }
    return result


def income_bracket(persona: Persona, thresholds: tuple[int, int]) -> str:
    """Label a persona by household-income tercile."""
    low, high = thresholds
    if persona.household_income <= low:
        return "lower third"
    if persona.household_income <= high:
        return "middle third"
    return "upper third"


def most_interesting(votes: Sequence[Vote], personas: Sequence[Persona]) -> Vote | None:
    """Pick the agent whose vote least matches its economic self-interest.

    A high-income household voting Yes, or a low-income one voting No, is more
    informative than a vote that simply tracks demographics.
    """
    by_id = {p.agent_id: p for p in personas}
    if not votes:
        return None

    def surprise(vote: Vote) -> float:
        persona = by_id.get(vote.agent_id)
        if persona is None:
            return 0.0
        expected_yes = persona.household_income < 100_000
        return 1.0 if expected_yes != (vote.vote == "Yes") else 0.0

    return max(votes, key=surprise)
