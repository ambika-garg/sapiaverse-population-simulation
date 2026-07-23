"""Compare true weighted population statistics against sampled draws."""

import pandas as pd

from census.cache import load_or_fetch
from census.client import CensusClient
from config.settings import get_settings
from personas.sampling import stratified_sample


def weighted_median(values: pd.Series, weights: pd.Series) -> float:
    """Median of `values` where each record counts `weights` times."""
    frame = pd.DataFrame({"value": values, "weight": weights}).dropna()
    frame = frame.sort_values("value")
    cumulative = frame["weight"].cumsum()
    return float(frame.loc[cumulative >= frame["weight"].sum() / 2, "value"].iloc[0])


def main() -> None:
    client = CensusClient(api_key=get_settings().census_api_key)
    pumas = client.discover_sf_pumas()
    frame = load_or_fetch(lambda: client.fetch_pums(pumas["PUMA"].tolist()))

    print("TRUE POPULATION (weighted by PWGTP)")
    print(f"  median age:    {weighted_median(frame['AGEP'], frame['PWGTP']):.0f}")
    print(f"  median income: ${weighted_median(frame['PINCP'], frame['PWGTP']):,.0f}")
    print(f"  unweighted age median: {frame['AGEP'].median():.0f}")

    print("\nSAMPLED DRAWS (10 seeds)")
    ages, incomes = [], []
    for seed in range(10):
        sample = stratified_sample(frame, seed=seed)
        ages.append(sample["AGEP"].median())
        incomes.append(sample["PINCP"].median())
        print(f"  seed {seed}: age {ages[-1]:.0f}, income ${incomes[-1]:,.0f}")

    mean_age = sum(ages) / len(ages)
    print(f"\n  age    across seeds: {min(ages):.0f}-{max(ages):.0f} (mean {mean_age:.1f})")
    print(f"  income across seeds: ${min(incomes):,.0f}-${max(incomes):,.0f}")


if __name__ == "__main__":
    main()
