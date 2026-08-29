"""Ingest play-level participation data from nflverse into raw.participation.

Participation carries the formation and personnel fields that load_pbp lacks:
offense_formation, offense_personnel, defense_personnel, defenders_in_box.

Beware the 2022/2023 schema break in the feed itself: through 2022 the
formation vocabulary is rich (EMPTY, I_FORM, JUMBO, SINGLEBACK, WILDCAT, ...)
and offense_personnel lists skill players only ("1 RB, 1 TE, 3 WR"); from 2023
formations collapse to SHOTGUN / UNDER CENTER / PISTOL and personnel becomes a
full 11-man list ("1 C, 2 G, 1 QB, 1 RB, 2 T, 1 TE, 3 WR"), with roughly 14%
of rows contaminated by defensive personnel. Raw lands both styles verbatim;
the staging model sorts them out.

Each season is pulled and loaded separately so one bad season does not block
the rest — same pattern as pfr_advstats.
"""

import nflreadpy as nfl
import pandas as pd
from src.db import load_to_raw


# Columns kept in raw. Everything else in the feed (player id lists, pass
# rusher counts, ngs route fields) is dropped until something needs it.
KEEP_COLUMNS = [
    "nflverse_game_id",
    "play_id",
    "possession_team",
    "offense_formation",
    "offense_personnel",
    "defense_personnel",
    "defenders_in_box",
]


def ingest_participation(seasons: list[int]) -> int:
    """Pull participation for the given seasons and load to raw.participation.

    Args:
        seasons: Seasons to pull, e.g. [2021, 2022, 2023].

    Returns:
        Total row count written across all seasons that succeeded.
    """
    print(f"Pulling participation for seasons: {seasons}")
    total = 0
    loaded_any = False

    for season in seasons:
        try:
            df = nfl.load_participation(seasons=season)

            # Convert Polars to pandas
            if hasattr(df, "to_pandas"):
                df = df.to_pandas()

            df.columns = df.columns.str.strip().str.lower()

            missing = [c for c in KEEP_COLUMNS if c not in df.columns]
            if missing:
                print(f"  ⚠ {season}: missing columns {missing}, loading the rest")
            df = df[[c for c in KEEP_COLUMNS if c in df.columns]]

            # First successful season replaces the table; the rest append.
            total += load_to_raw(
                df, "participation", if_exists="append" if loaded_any else "replace"
            )
            loaded_any = True
        except Exception as e:
            print(f"  ⚠ {season} failed: {type(e).__name__}: {e}")

    return total
