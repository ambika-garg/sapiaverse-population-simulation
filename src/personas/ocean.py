"""Synthesis of Big Five (OCEAN) personality profiles.

OCEAN traits are NOT in Census data. They are generated here from weak age
priors, and are the single largest source of *modeled* rather than *measured*
variance in this simulation. Documented as such in the README.
"""

import numpy as np

from personas.models import OceanProfile

TRAIT_MEAN = 0.5
TRAIT_SD = 0.18
TRAIT_FLOOR, TRAIT_CEILING = 0.05, 0.95
AGE_PIVOT, AGE_SCALE = 45, 30

# Directions broadly reported in the Big Five aging literature. Deliberately
# small coefficients: these are nudges, not deterministic mappings.
AGE_COEFFICIENTS = {
    "openness": -0.06,
    "conscientiousness": 0.08,
    "extraversion": -0.03,
    "agreeableness": 0.07,
    "neuroticism": -0.07,
}


def synthesize_ocean(age: int, rng: np.random.Generator) -> OceanProfile:
    """Draw a Big Five profile, lightly conditioned on age."""
    age_offset = (age - AGE_PIVOT) / AGE_SCALE
    scores = {
        trait: round(
            float(
                np.clip(
                    rng.normal(TRAIT_MEAN + coefficient * age_offset, TRAIT_SD),
                    TRAIT_FLOOR,
                    TRAIT_CEILING,
                )
            ),
            2,
        )
        for trait, coefficient in AGE_COEFFICIENTS.items()
    }
    return OceanProfile(**scores)
