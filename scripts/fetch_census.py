"""One-shot script: pull SF PUMS microdata and print a sanity report."""

import logging

from census.cache import load_or_fetch
from census.client import CensusClient
from config.settings import get_settings


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    settings = get_settings()
    client = CensusClient(api_key=settings.census_api_key)

    pumas = client.discover_sf_pumas()
    print("\nSan Francisco PUMAs:")
    print(pumas.to_string(index=False))

    frame = load_or_fetch(lambda: client.fetch_pums(pumas["PUMA"].tolist()))

    print(f"\nRows (adults 18+): {len(frame):,}")
    print(f"Weighted population: {frame['PWGTP'].sum():,.0f}")
    age_median = frame["AGEP"].median()
    age_min, age_max = frame["AGEP"].min(), frame["AGEP"].max()
    print(f"\nAge:    median {age_median:.0f}, range {age_min}-{age_max}")
    print(f"Income: median ${frame['PINCP'].median():,.0f}")
    print(f"\nRecords per PUMA:\n{frame['PUMA'].value_counts().to_string()}")


if __name__ == "__main__":
    main()
