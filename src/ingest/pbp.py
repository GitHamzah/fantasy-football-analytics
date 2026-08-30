"""Ingest play-by-play data from nflverse into raw.pbp.

Only the columns needed for matchup analysis are kept and only real offensive
snaps (pass/run) are landed — the full feed is ~370 columns and includes
kickoffs, punts, kneels and no-plays that matchup analysis never touches.
Filtered this way a season is ~34k rows instead of ~49k.

pbp's game_id is already the nflverse format ("2025_01_ARI_NO"); it is renamed
to nflverse_game_id so the join key to raw.participation is spelled the same
on both sides.

Each season is pulled and loaded separately so one bad season does not block
the rest — same pattern as participation.
"""

import nflreadpy as nfl
import pandas as pd
from src.db import load_to_raw


# Feed column -> raw column. game_id carries the nflverse id in pbp.
KEEP_COLUMNS = {
    "game_id": "nflverse_game_id",
    "play_id": "play_id",
    "posteam": "posteam",
    "defteam": "defteam",
    "season": "season",
    "week": "week",
    "play_type": "play_type",
    "yards_gained": "yards_gained",
    "passing_yards": "passing_yards",
    "rushing_yards": "rushing_yards",
    "receiving_yards": "receiving_yards",
    "touchdown": "touchdown",
    "interception": "interception",
    "fumble_lost": "fumble_lost",
    "epa": "epa",
    "success": "success",
    "down": "down",
    "ydstogo": "ydstogo",
    "score_differential": "score_differential",
    "wp": "wp",
    # Not in the original spec, but receptions counted as receiving_yards > 0
    # would drop 0-yard and negative-yard catches; this flag counts them right.
    "complete_pass": "complete_pass",
    "receiver_player_id": "receiver_player_id",
    "receiver_player_name": "receiver_player_name",
    "rusher_player_id": "rusher_player_id",
    "rusher_player_name": "rusher_player_name",
    "passer_player_id": "passer_player_id",
    "passer_player_name": "passer_player_name",
}


def ingest_pbp(seasons: list[int]) -> int:
    """Pull pass/run plays for the given seasons and load to raw.pbp.

    Args:
        seasons: Seasons to pull, e.g. [2021, 2022, 2023].

    Returns:
        Total row count written across all seasons that succeeded.
    """
    print(f"Pulling play-by-play for seasons: {seasons}")
    total = 0
    loaded_any = False

    for season in seasons:
        try:
            df = nfl.load_pbp(seasons=season)

            # Convert Polars to pandas
            if hasattr(df, "to_pandas"):
                df = df.to_pandas()

            df.columns = df.columns.str.strip().str.lower()

            missing = [c for c in KEEP_COLUMNS if c not in df.columns]
            if missing:
                print(f"  ⚠ {season}: missing columns {missing}, loading the rest")
            keep = {c: n for c, n in KEEP_COLUMNS.items() if c in df.columns}
            df = df[list(keep)].rename(columns=keep)

            # Real offensive snaps only. play_type is NULL on penalties and
            # timeouts, so the IN filter drops those too.
            df = df[df["play_type"].isin(["pass", "run"])]

            # First successful season replaces the table; the rest append.
            total += load_to_raw(
                df, "pbp", if_exists="append" if loaded_any else "replace"
            )
            loaded_any = True
        except Exception as e:
            print(f"  ⚠ {season} failed: {type(e).__name__}: {e}")

    return total
