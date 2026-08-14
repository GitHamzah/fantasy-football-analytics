"""Ingest Pro Football Reference advanced stats from nflverse into the raw schema.

PFR advanced stats come in four flavours (pass, rush, rec, def), each loaded
separately at weekly summary level and landed in its own raw table. Each stat
type is wrapped in its own try/except so one bad pull does not block the rest.
"""

import nflreadpy as nfl
import pandas as pd
from src.db import load_to_raw


# stat_type passed to nflreadpy -> raw table name (without schema prefix)
STAT_TYPES = {
    "pass": "pfr_pass",
    "rush": "pfr_rush",
    "rec": "pfr_rec",
    "def": "pfr_def",
}


def ingest_pfr_advstats(seasons: list[int]) -> dict[str, int]:
    """Pull PFR advanced stats for the given seasons and load each type to raw.

    Args:
        seasons: Seasons to pull, e.g. [2021, 2022, 2023].

    Returns:
        Mapping of raw table name -> row count written. Stat types that failed
        are omitted from the result.
    """
    print(f"Pulling pfr_advstats for seasons: {seasons}")
    results: dict[str, int] = {}

    for stat_type, table_name in STAT_TYPES.items():
        try:
            df = nfl.load_pfr_advstats(
                seasons=seasons,
                stat_type=stat_type,
                summary_level="week",
            )

            # Convert Polars to pandas
            if hasattr(df, "to_pandas"):
                df = df.to_pandas()

            df.columns = df.columns.str.strip().str.lower()

            results[table_name] = load_to_raw(df, table_name)
        except Exception as e:
            print(f"  ⚠ {stat_type} failed: {type(e).__name__}: {e}")

    return results
