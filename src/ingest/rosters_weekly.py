"""Ingest weekly roster snapshots from nflverse into raw.rosters_weekly."""

import nflreadpy as nfl
import pandas as pd
from src.db import load_to_raw


def ingest_rosters_weekly(seasons: list[int]) -> pd.DataFrame:
    """Pull weekly roster data for the given seasons and load to raw.

    Returns one row per player per week showing team, position,
    jersey number, and roster status for that week.
    """
    print(f"Pulling rosters_weekly for seasons: {seasons}")
    df = nfl.load_rosters_weekly(seasons=seasons)

    # Convert Polars to pandas
    if hasattr(df, "to_pandas"):
        df = df.to_pandas()

    df.columns = df.columns.str.strip().str.lower()

    load_to_raw(df, "rosters_weekly")
    return df
