"""
sync_to_neon.py — Sync mart data from SQL Server to Neon Postgres.

Run from project root with venv activated:
    python sync_to_neon.py

Reads from your local SQL Server mart schema and writes to Neon Postgres.
This is the bridge between your development environment and production.
"""

import os
import pandas as pd
from sqlalchemy import create_engine, text
from src.config import load_config

# Neon connection from environment variable
NEON_URL = os.environ.get("NEON_DATABASE_URL", "")


def get_sqlserver_engine():
    """Get SQL Server engine from existing config."""
    import urllib
    cfg = load_config()["database"]
    params = urllib.parse.quote_plus(
        f"DRIVER={{{cfg['driver']}}};"
        f"SERVER={cfg['server']},{cfg['port']};"
        f"DATABASE={cfg['database']};"
        f"UID={cfg['username']};"
        f"PWD={cfg['password']};"
        f"TrustServerCertificate=yes;"
    )
    return create_engine(f"mssql+pyodbc:///?odbc_connect={params}")


def get_neon_engine():
    """Get Neon Postgres engine."""
    if not NEON_URL:
        raise ValueError(
            "NEON_DATABASE_URL environment variable not set.\n"
            "Set it with: $env:NEON_DATABASE_URL = 'postgresql://...'"
        )
    return create_engine(NEON_URL)


# Tables to sync from mart schema
MART_TABLES = [
    ("mart.dim_player", "dim_player"),
    ("mart.dim_team", "dim_team"),
    ("mart.dim_week", "dim_week"),
    ("mart.dim_game", "dim_game"),
    ("mart.dim_scoring_format", "dim_scoring_format"),
    ("mart.fact_player_week", "fact_player_week"),
    ("mart.team_defense", "team_defense"),
    ("mart.pfr_advstats", "pfr_advstats"),
    ("mart.formation", "formation"),
    ("mart.def_formation", "def_formation"),
    # fact_play_matchup itself stays local: ~170K rows is too heavy for the
    # sync, and the API only needs these aggregations.
    ("mart.player_vs_defense", "player_vs_defense"),
    ("mart.team_matchup", "team_matchup"),
    # Sleeper league marts — flat tables so the API can serve league features
    # from Neon; the sleeper schema itself never leaves SQL Server.
    ("mart.my_roster", "my_roster"),
    ("mart.league_standings", "league_standings"),
    ("mart.league_matchup", "league_matchup"),
    ("mart.schedule_projection", "schedule_projection"),
    ("mart.season_projection", "season_projection"),
]


def sync():
    """Full sync of mart data from SQL Server to Neon."""
    ss_engine = get_sqlserver_engine()
    neon_engine = get_neon_engine()

    print("=" * 60)
    print("Syncing mart data: SQL Server → Neon Postgres")
    print("=" * 60)

    for source_table, target_table in MART_TABLES:
        print(f"\n  {source_table} → {target_table}")

        # Read from SQL Server
        df = pd.read_sql(f"SELECT * FROM {source_table}", ss_engine)
        print(f"    Read {len(df):,} rows from SQL Server")

        # Write to Neon (replace = drop and recreate)
        df.to_sql(
            target_table,
            neon_engine,
            if_exists="replace",
            index=False,
            method="multi",
            chunksize=5000,
        )
        print(f"    Wrote {len(df):,} rows to Neon")

    # Create indexes on Neon for query performance
    print("\nCreating indexes...")
    with neon_engine.begin() as conn:
        indexes = [
            "CREATE INDEX IF NOT EXISTS ix_fpw_gsis ON fact_player_week(gsis_id)",
            "CREATE INDEX IF NOT EXISTS ix_fpw_season ON fact_player_week(season, week)",
            "CREATE INDEX IF NOT EXISTS ix_fpw_team ON fact_player_week(recent_team)",
            "CREATE INDEX IF NOT EXISTS ix_player_gsis ON dim_player(gsis_id)",
            "CREATE INDEX IF NOT EXISTS ix_game_id ON dim_game(game_id)",
            "CREATE INDEX IF NOT EXISTS ix_week_key ON dim_week(week_key)",
        ]
        for idx in indexes:
            conn.execute(text(idx))
    print("  Indexes created.")

    print("\n" + "=" * 60)
    print("Sync complete!")
    print("=" * 60)


if __name__ == "__main__":
    sync()
