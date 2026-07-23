"""Assemble cleaned PUMS rows into Persona objects."""

import numpy as np
import pandas as pd

from census.constants import RANDOM_SEED
from personas.enrich import (
    clean_ethnicity,
    clean_housing,
    clean_occupation,
    parse_neighborhood,
)
from personas.models import Persona
from personas.names import assign_names
from personas.ocean import synthesize_ocean


def _as_int(value: object) -> int:
    """Coerce a possibly-missing PUMS numeric to an int."""
    return 0 if pd.isna(value) else int(value)


def build_personas(
    sample: pd.DataFrame, puma_names: pd.DataFrame, seed: int = RANDOM_SEED
) -> list[Persona]:
    """Turn sampled microdata rows into fully-formed residents."""
    rng = np.random.default_rng(seed)
    names = assign_names(len(sample), rng)
    puma_lookup = dict(zip(puma_names["PUMA"], puma_names["NAME"], strict=True))

    personas = []
    for position, (_, row) in enumerate(sample.iterrows()):
        age = _as_int(row["AGEP"])
        personas.append(
            Persona(
                agent_id=f"sf-{position:03d}",
                name=names[position],
                age=age,
                puma=str(row["PUMA"]),
                neighborhood=parse_neighborhood(puma_lookup.get(str(row["PUMA"]), "")),
                ethnicity=clean_ethnicity(row["RAC1P_label"], row["HISP"]),
                occupation=clean_occupation(row["OCCP_label"], age),
                education=row["SCHL_label"],
                personal_income=_as_int(row["PINCP"]),
                household_income=_as_int(row["HINCP"]),
                housing=clean_housing(row["TEN_label"]),
                ocean=synthesize_ocean(age, rng),
            )
        )
    return personas
