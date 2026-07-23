"""Adapter for the US Census Bureau API.

This is the only module in the codebase that knows the Census API exists.
Everything downstream receives clean DataFrames.
"""

import logging

import httpx
import pandas as pd

from census.constants import (
    CA_STATE_FIPS,
    CENSUS_BASE_URL,
    CODED_VARIABLES,
    NUMERIC_VARIABLES,
    PERSON_VARIABLES,
    PUMS_SURVEY,
    PUMS_YEAR,
    SF_COUNTY_NAME,
    VOTING_AGE,
)

logger = logging.getLogger(__name__)


class CensusAPIError(RuntimeError):
    """Raised when the Census API returns an unusable response."""


class CensusClient:
    """Fetches ACS PUMS microdata for San Francisco."""

    def __init__(self, api_key: str | None = None, timeout: float = 60.0) -> None:
        self._api_key = api_key
        self._timeout = timeout

    def _get(self, path: str, params: dict[str, str]) -> list[list[str]]:
        """Issue a GET against the Census API and return the raw JSON matrix."""
        query = dict(params)
        if self._api_key:
            query["key"] = self._api_key

        response = httpx.get(
            f"{CENSUS_BASE_URL}/{path}",
            params=query,
            timeout=self._timeout,
            follow_redirects=True,
        )
        if response.status_code != httpx.codes.OK:
            raise CensusAPIError(
                f"Census API returned {response.status_code}: {response.text[:200]}"
            )

        content_type = response.headers.get("content-type", "")
        if "json" not in content_type:
            raise CensusAPIError(
                f"Census API returned non-JSON response (content-type: {content_type!r}). "
                f"Check your CENSUS_API_KEY. First 200 chars: {response.text[:200]}"
            )

        payload = response.json()
        if not isinstance(payload, list) or len(payload) < 2:
            raise CensusAPIError("Census API returned no data rows")
        return payload

    @staticmethod
    def _to_frame(payload: list[list[str]]) -> pd.DataFrame:
        """Convert the Census array-of-arrays (header row first) to a DataFrame."""
        header, *rows = payload
        return pd.DataFrame(rows, columns=header)

    @staticmethod
    def _filter_sf_pumas(frame: pd.DataFrame) -> pd.DataFrame:
        """Keep only PUMAs whose name begins with San Francisco County.

        Anchoring at the start matters: a substring match would also catch
        South San Francisco, which is in San Mateo County.
        """
        mask = frame["NAME"].str.strip().str.startswith(SF_COUNTY_NAME)
        sf = frame[mask].rename(columns={"public use microdata area": "PUMA"})
        if sf.empty:
            raise CensusAPIError(f"No PUMAs matched '{SF_COUNTY_NAME}'")
        return sf[["PUMA", "NAME"]].reset_index(drop=True)

    def discover_sf_pumas(self) -> pd.DataFrame:
        """Find San Francisco's PUMA codes by name, rather than hardcoding them."""
        payload = self._get(
            f"{PUMS_YEAR}/{PUMS_SURVEY}",
            {
                "get": "NAME",
                "for": "public use microdata area:*",
                "in": f"state:{CA_STATE_FIPS}",
            },
        )
        sf = self._filter_sf_pumas(self._to_frame(payload))
        logger.info("Discovered %d San Francisco PUMAs", len(sf))
        return sf

    def fetch_pums(self, puma_codes: list[str]) -> pd.DataFrame:
        """Fetch person-level PUMS records for the given PUMAs."""
        frames = []
        for puma in puma_codes:
            payload = self._get(
                f"{PUMS_YEAR}/{PUMS_SURVEY}/pums",
                {
                    "get": ",".join(PERSON_VARIABLES),
                    "for": f"public use microdata area:{puma}",
                    "in": f"state:{CA_STATE_FIPS}",
                },
            )
            frames.append(self._to_frame(payload))
            logger.info("Fetched PUMA %s (%d rows)", puma, len(frames[-1]))

        return self._clean(pd.concat(frames, ignore_index=True))

    @staticmethod
    def _clean(frame: pd.DataFrame) -> pd.DataFrame:
        """Cast numeric columns and restrict to voting-age adults."""
        for column in NUMERIC_VARIABLES:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")

        adults = frame[frame["AGEP"] >= VOTING_AGE].copy()
        return adults.reset_index(drop=True)

    def fetch_variable_labels(self, variable: str) -> dict[str, str]:
        """Fetch official value labels for a coded PUMS variable.

        The Census publishes a metadata document per variable, so we look up
        labels at the source rather than hardcoding a mapping.
        """
        url = f"{CENSUS_BASE_URL}/{PUMS_YEAR}/{PUMS_SURVEY}/pums/variables/{variable}.json"
        response = httpx.get(url, timeout=self._timeout)
        if response.status_code != httpx.codes.OK:
            raise CensusAPIError(f"Label lookup failed for {variable}: {response.status_code}")

        items = response.json().get("values", {}).get("item")
        if not items:
            raise CensusAPIError(f"No value labels published for {variable}")
        return {str(code): str(label) for code, label in items.items()}

    def fetch_all_labels(self) -> dict[str, dict[str, str]]:
        """Fetch label dictionaries for every coded variable."""
        return {variable: self.fetch_variable_labels(variable) for variable in CODED_VARIABLES}
