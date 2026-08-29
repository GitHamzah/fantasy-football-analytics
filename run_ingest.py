"""
run_ingest.py — Raw ingestion runner.

Pulls nflverse data and lands it in the raw schema of FantasyFootball.
Run from the project root with the venv activated:

    python run_ingest.py

To ingest specific seasons:

    python run_ingest.py --seasons 2024 2025 2026
"""

import argparse
import time
from src.config import load_config
from src.ingest.player_stats import ingest_player_stats
from src.ingest.schedules import ingest_schedules
from src.ingest.players import ingest_players
from src.ingest.rosters_weekly import ingest_rosters_weekly


def main():
    parser = argparse.ArgumentParser(description="Ingest nflverse data into SQL Server.")
    parser.add_argument(
        "--seasons",
        nargs="+",
        type=int,
        default=None,
        help="Seasons to ingest (e.g. --seasons 2023 2024). Defaults to config file.",
    )
    args = parser.parse_args()

    config = load_config()
    seasons = args.seasons or config["ingestion"]["seasons"]

    print(f"{'='*60}")
    print(f"Fantasy Football Analytics — Raw Ingestion")
    print(f"Target: {config['database']['server']}:{config['database']['port']}")
    print(f"Database: {config['database']['database']}")
    print(f"Seasons: {seasons}")
    print(f"{'='*60}\n")

    start = time.time()

    # 1. Players (full universe, not season-specific)
    print("[1/6] Players")
    try:
        ingest_players()
    except Exception as e:
        print(f"  ⚠ Players failed: {e}")
    print()

    # 2. Schedules
    print("[2/6] Schedules")
    try:
        ingest_schedules(seasons)
    except Exception as e:
        print(f"  ⚠ Schedules failed: {e}")
    print()

    # 3. Player stats (weekly) — may not exist for future seasons
    print("[3/6] Player Stats")
    try:
        ingest_player_stats(seasons)
    except Exception as e:
        print(f"  ⚠ Player Stats failed: {e}")
        print(f"  Retrying without latest season...")
        try:
            ingest_player_stats(seasons[:-1])
        except Exception as e2:
            print(f"  ⚠ Retry also failed: {e2}")
    print()

    # 4. Weekly rosters
    print("[4/6] Rosters Weekly")
    try:
        ingest_rosters_weekly(seasons)
    except Exception as e:
        print(f"  ⚠ Rosters Weekly failed: {e}")
        print(f"  Retrying without latest season...")
        try:
            ingest_rosters_weekly(seasons[:-1])
        except Exception as e2:
            print(f"  ⚠ Retry also failed: {e2}")
    print()

    # 5. PFR Advanced Stats
    print("[5/6] PFR Advanced Stats")
    try:
        from src.ingest.pfr_advstats import ingest_pfr_advstats
        ingest_pfr_advstats(seasons)
    except Exception as e:
        print(f"  ⚠ PFR Advanced Stats failed: {e}")
    print()

    # 6. Participation (formations & personnel)
    print("[6/6] Participation (formations & personnel)")
    try:
        from src.ingest.participation import ingest_participation
        ingest_participation(seasons)
    except Exception as e:
        print(f"  ⚠ Participation failed: {e}")
    print()

    elapsed = time.time() - start
    print(f"{'='*60}")
    print(f"Raw ingestion complete in {elapsed:.1f}s")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
