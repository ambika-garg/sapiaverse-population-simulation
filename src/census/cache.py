"""Parquet caching for Census pulls, so we hit the network once."""

import logging
from collections.abc import Callable
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

DEFAULT_CACHE_PATH = Path("data/sf_pums.parquet")


def load_or_fetch(
    fetch_fn: Callable[[], pd.DataFrame],
    path: Path = DEFAULT_CACHE_PATH,
    refresh: bool = False,
) -> pd.DataFrame:
    """Return cached microdata, fetching and caching it if absent."""
    if path.exists() and not refresh:
        logger.info("Loading cached Census data from %s", path)
        return pd.read_parquet(path)

    logger.info("Cache miss — fetching from Census API")
    frame = fetch_fn()
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path, index=False)
    logger.info("Cached %d rows to %s", len(frame), path)
    return frame
