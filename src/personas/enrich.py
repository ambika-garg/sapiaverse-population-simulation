"""Convert raw PUMS labels into natural language suitable for prompting."""

import re

SOC_PREFIX = re.compile(r"^[A-Z]{3}-")
RETIREMENT_AGE = 62
NON_HISPANIC_CODES = {"1", "01"}


def parse_neighborhood(puma_name: str) -> str:
    """Extract the neighborhood description from a PUMA's official name."""
    tail = puma_name.split("--", 1)[1] if "--" in puma_name else puma_name
    return tail.split(" PUMA")[0].strip()


def clean_occupation(label: str, age: int) -> str:
    """Resolve occupation, translating PUMS 'N/A' into a real life stage."""
    if label.startswith("N/A") or label == "Not reported":
        return "retired" if age >= RETIREMENT_AGE else "not currently employed"
    return SOC_PREFIX.sub("", label).strip()


def clean_housing(label: str) -> str:
    """Describe the household's housing situation, not the person's ownership."""
    lowered = label.lower()
    if "without payment" in lowered:
        return "lives rent-free"
    if "mortgage" in lowered:
        return "lives in a home owned with a mortgage"
    if "free and clear" in lowered:
        return "lives in a home owned outright"
    if "rent" in lowered:
        return "rents their home"
    if "gq" in lowered or "group" in lowered:
        return "lives in group quarters (dormitory, shelter, or care facility)"
    return "housing situation not reported"


def clean_ethnicity(race_label: str, hispanic_code: object) -> str:
    """Combine PUMS race and Hispanic-origin fields into one ethnicity label."""
    if str(hispanic_code).strip() not in NON_HISPANIC_CODES:
        return "Hispanic or Latino"
    return race_label.replace(" alone", "").strip()
