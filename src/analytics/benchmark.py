"""Compare the simulation against the real-world result."""

from dataclasses import dataclass

from scenarios.registry import PROP_F_ACTUAL_YES_PCT


@dataclass
class BenchmarkResult:
    """Simulated vs actual outcome."""

    simulated_yes_pct: float
    actual_yes_pct: float
    delta_pct_points: float

    @property
    def direction(self) -> str:
        if self.delta_pct_points > 0:
            return "over-predicted support"
        if self.delta_pct_points < 0:
            return "under-predicted support"
        return "matched"

    def describe(self) -> str:
        return (
            f"Simulated {self.simulated_yes_pct:.1f}% Yes vs actual "
            f"{self.actual_yes_pct:.1f}% (SF Prop F, 2021). "
            f"Delta {self.delta_pct_points:+.1f} points - {self.direction}."
        )


def benchmark(simulated_yes_pct: float) -> BenchmarkResult:
    """Compute the gap between simulation and reality."""
    return BenchmarkResult(
        simulated_yes_pct=simulated_yes_pct,
        actual_yes_pct=PROP_F_ACTUAL_YES_PCT,
        delta_pct_points=round(simulated_yes_pct - PROP_F_ACTUAL_YES_PCT, 1),
    )


def behavioural_delta(baseline_yes_pct: float, arm_yes_pct: float) -> float:
    """Percentage-point movement between two runs."""
    return round(arm_yes_pct - baseline_yes_pct, 1)
