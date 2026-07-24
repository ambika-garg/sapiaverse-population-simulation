"""Declarative scenario definitions.

Adding a scenario is a config entry, not a code change.
"""

from dataclasses import dataclass

PROP_F_ACTUAL_YES_PCT = 60.8


@dataclass(frozen=True)
class Scenario:
    """One question put to the whole population."""

    scenario_id: str
    question: str
    incentive: str | None = None


PROP_X = Scenario(
    scenario_id="prop_x",
    question=(
        "San Francisco is voting on a measure that would cap food delivery app "
        "fees (DoorDash, Uber Eats) at 15%. As a resident, would you vote Yes "
        "or No? Give your single most important reason in one sentence."
    ),
)

PROP_X_CREDIT = Scenario(
    scenario_id="prop_x_credit",
    question=(
        "San Francisco is voting on a measure that would cap food delivery app "
        "fees (DoorDash, Uber Eats) at 15%. Would you vote Yes or No? Give your "
        "single most important reason in one sentence."
    ),
    incentive="DoorDash offers you a $5 account credit if you vote No.",
)

SCENARIOS = {s.scenario_id: s for s in (PROP_X, PROP_X_CREDIT)}
