"""Sample 30 San Franciscans from cached PUMS microdata."""

import logging

import pandas as pd

from census.cache import load_or_fetch
from census.client import CensusClient
from config.settings import get_settings
from personas.builder import build_personas
from personas.decode import decode_frame
from personas.sampling import stratified_sample


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    pd.set_option("display.width", 200)

    client = CensusClient(api_key=get_settings().census_api_key)
    pumas = client.discover_sf_pumas()
    frame = load_or_fetch(lambda: client.fetch_pums(pumas["PUMA"].tolist()))

    labels = client.fetch_all_labels()
    decoded = decode_frame(frame, labels)
    sample = stratified_sample(decoded)
    personas = build_personas(sample, pumas)

    for person in personas:
        traits = ", ".join(
            f"{trait[:4]} {person.ocean.band(getattr(person.ocean, trait))}"
            for trait in (
                "openness",
                "conscientiousness",
                "extraversion",
                "agreeableness",
                "neuroticism",
            )
        )
        print(
            f"\n[{person.agent_id}] {person.name}, {person.age} — {person.neighborhood}"
            f"\n    {person.ethnicity} | {person.occupation} | {person.education}"
            f"\n    income ${person.personal_income:,} (household ${person.household_income:,})"
            f"\n    {person.housing}"
            f"\n    {traits}"
        )


if __name__ == "__main__":
    main()
