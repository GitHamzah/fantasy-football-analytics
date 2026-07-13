"""
run_ingest.py — Phase 1 ingestion runner.

Pulls nflverse data and lands it in the raw schema of FantasyFootball.
Run from the project root with the venv activated:

    python run_ingest.py

To ingest a specific season only:

    python run_ingest.py --seasons 2024
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
    print("[1/4] Players")
    ingest_players()
    print()

    # 2. Schedules
    print("[2/4] Schedules")
    ingest_schedules(seasons)
    print()

    # 3. Player stats (weekly)
    print("[3/4] Player Stats")
    ingest_player_stats(seasons)
    print()

    # 4. Weekly rosters
    print("[4/4] Rosters Weekly")
    ingest_rosters_weekly(seasons)
    print()

    elapsed = time.time() - start
    print(f"{'='*60}")
    print(f"Raw ingestion complete in {elapsed:.1f}s")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
