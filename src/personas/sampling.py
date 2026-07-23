"""Stratified, weight-aware sampling of PUMS records."""

import math

import pandas as pd

from census.constants import RANDOM_SEED, TARGET_POPULATION_SIZE


def allocate_by_stratum(weights: pd.Series, total: int) -> dict[str, int]:
    """Split `total` agents across strata proportionally to population weight.

    Uses the largest-remainder method so the allocation sums exactly to
    `total`, with a floor of one agent per stratum to guarantee coverage.
    """
    shares = weights / weights.sum()
    exact = shares * total
    allocation = {stratum: max(1, math.floor(value)) for stratum, value in exact.items()}

    remainders = (exact - exact.apply(math.floor)).sort_values(ascending=False)
    difference = total - sum(allocation.values())

    for stratum in remainders.index:
        if difference == 0:
            break
        if difference > 0:
            allocation[stratum] += 1
            difference -= 1

    while difference < 0:
        largest = max(allocation, key=lambda key: allocation[key])
        allocation[largest] -= 1
        difference += 1

    return allocation


def stratified_sample(
    frame: pd.DataFrame,
    size: int = TARGET_POPULATION_SIZE,
    seed: int = RANDOM_SEED,
) -> pd.DataFrame:
    """Draw `size` records, stratified by PUMA and weighted by PWGTP."""
    weights_by_puma = frame.groupby("PUMA")["PWGTP"].sum()
    allocation = allocate_by_stratum(weights_by_puma, size)

    drawn = [
        group.sample(n=allocation[puma], weights="PWGTP", random_state=seed + offset)
        for offset, (puma, group) in enumerate(frame.groupby("PUMA"))
    ]
    return pd.concat(drawn).sample(frac=1, random_state=seed).reset_index(drop=True)
