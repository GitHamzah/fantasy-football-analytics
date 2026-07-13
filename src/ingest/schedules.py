"""Ingest game schedules from nflverse into raw.schedules."""

import nflreadpy as nfl
import pandas as pd
from src.db import load_to_raw


def ingest_schedules(seasons: list[int]) -> pd.DataFrame:
    """Pull game schedules for the given seasons and load to raw.

    Returns one row per game with teams, scores, dates, and game metadata.
    """
    print(f"Pulling schedules for seasons: {seasons}")
    df = nfl.load_schedules(seasons=seasons)

    # Convert Polars to pandas
    if hasattr(df, "to_pandas"):
        df = df.to_pandas()

    df.columns = df.columns.str.strip().str.lower()

    load_to_raw(df, "schedules")
    return df
