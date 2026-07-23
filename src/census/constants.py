"""Constants for Census API access."""

CENSUS_BASE_URL = "https://api.census.gov/data"
PUMS_YEAR = 2023
PUMS_SURVEY = "acs/acs1"
CA_STATE_FIPS = "06"
SF_COUNTY_NAME = "San Francisco County"

# PUMS person variables we pull. Keys are Census codes; values document them.
PERSON_VARIABLES: dict[str, str] = {
    "PUMA": "Public Use Microdata Area code",
    "AGEP": "Age in years",
    "PINCP": "Personal income, past 12 months (USD)",
    "HINCP": "Household income, past 12 months (USD)",
    "OCCP": "Occupation code",
    "SCHL": "Educational attainment",
    "TEN": "Housing tenure (owned vs rented)",
    "RAC1P": "Race, recoded",
    "HISP": "Hispanic origin",
    "PWGTP": "Person weight — records represent ~this many people",
}

NUMERIC_VARIABLES = frozenset({"AGEP", "PINCP", "HINCP", "PWGTP"})
VOTING_AGE = 18
# Variables returned as numeric codes that need label lookup.
CODED_VARIABLES = frozenset({"OCCP", "SCHL", "TEN", "RAC1P", "HISP"})

TARGET_POPULATION_SIZE = 30
RANDOM_SEED = 42
