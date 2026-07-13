"""Ingest weekly player stats from nflverse into raw.player_stats."""

import nflreadpy as nfl
import pandas as pd
from src.db import load_to_raw


def ingest_player_stats(seasons: list[int]) -> pd.DataFrame:
    """Pull weekly player stats for the given seasons and load to raw.

    Uses nflreadpy.load_player_stats() which returns one row per
    player per week with passing, rushing, receiving stat components.
    """
    print(f"Pulling player_stats for seasons: {seasons}")
    df = nfl.load_player_stats(seasons=seasons)

    # Convert Polars to pandas
    if hasattr(df, "to_pandas"):
        df = df.to_pandas()

    df.columns = df.columns.str.strip().str.lower()

    load_to_raw(df, "player_stats")
    return df
