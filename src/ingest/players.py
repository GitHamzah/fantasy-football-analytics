"""Ingest player identity and biographical data into raw.players."""

import nflreadpy as nfl
import pandas as pd
from src.db import load_to_raw


def ingest_players() -> pd.DataFrame:
    """Pull the full player universe and load to raw.

    This is not season-specific — it returns all known players
    with IDs, names, positions, teams, draft info, etc.
    """
    print("Pulling players (full universe)")
    df = nfl.load_players()

    # Convert Polars to pandas
    if hasattr(df, "to_pandas"):
        df = df.to_pandas()

    df.columns = df.columns.str.strip().str.lower()

    load_to_raw(df, "players")
    return df
