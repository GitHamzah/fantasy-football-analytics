"""Ingest Hamzah's Sleeper fantasy leagues into the sleeper schema.

Pulls every league on the account across 2023-2026: league settings, managers,
rosters, weekly matchups, draft picks and transactions, plus the full Sleeper
player universe as a bridge table (sleeper_id -> gsis_id) into nflverse data.

The Sleeper API is free, read-only and unauthenticated; a 0.5s sleep between
calls keeps the run well under the ~90 requests/minute limit. List/dict
columns (players, starters, players_points, adds, drops) are stored as their
string representations — dbt staging can parse them when something needs the
elements.

Run from the project root:  python -m src.ingest.sleeper
"""

import time

import nflreadpy as nfl
import pandas as pd
import requests
from sqlalchemy import text

from src.db import get_engine

SLEEPER_BASE = "https://api.sleeper.app/v1"
USER_ID = "997944313776496640"
SEASONS = [2023, 2024, 2025, 2026]


def _get(url):
    """GET with rate limiting."""
    resp = requests.get(url, timeout=30)
    time.sleep(0.5)  # respect rate limits
    resp.raise_for_status()
    return resp.json()


def _load_to_sleeper(df, table_name, engine, if_exists="replace"):
    """Load a DataFrame into the sleeper schema.

    Chunked the same way as src.db.load_to_raw: SQL Server allows 2100 bind
    parameters per batch, so the chunk size is derived from column count.
    """
    safe_chunksize = max(1, 2000 // max(1, len(df.columns)))
    df.to_sql(
        table_name,
        engine,
        schema="sleeper",
        if_exists=if_exists,
        index=False,
        method="multi",
        chunksize=safe_chunksize,
    )
    print(f"    sleeper.{table_name}: {len(df):,} rows")


def ingest_sleeper():
    engine = get_engine()

    # Ensure schema exists
    with engine.begin() as conn:
        conn.execute(text(
            "IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'sleeper') "
            "EXEC('CREATE SCHEMA sleeper')"
        ))

    all_leagues = []
    all_users = []
    all_rosters = []
    all_matchups = []
    all_draft_picks = []
    all_transactions = []

    # 1. Get all leagues across all seasons
    print("  Discovering leagues...")
    for season in SEASONS:
        leagues = _get(f"{SLEEPER_BASE}/user/{USER_ID}/leagues/nfl/{season}")
        if not leagues:
            continue
        for lg in leagues:
            lg["_season"] = season
            all_leagues.append(lg)

    print(f"  Found {len(all_leagues)} leagues across {len(SEASONS)} seasons")

    # 2. Build leagues table
    leagues_df = pd.DataFrame([{
        "league_id": lg["league_id"],
        "name": lg["name"],
        "season": lg["_season"],
        "status": lg["status"],
        "total_rosters": lg["total_rosters"],
        "scoring_type": (
            "ppr" if lg.get("scoring_settings", {}).get("rec", 0) == 1.0
            else "half_ppr" if lg.get("scoring_settings", {}).get("rec", 0) == 0.5
            else "standard"
        ),
        "rec_scoring": lg.get("scoring_settings", {}).get("rec", 0),
        "pass_td": lg.get("scoring_settings", {}).get("pass_td", 4),
        "roster_positions": str(lg.get("roster_positions", [])),
        "previous_league_id": lg.get("previous_league_id"),
        "draft_id": lg.get("draft_id"),
    } for lg in all_leagues])
    _load_to_sleeper(leagues_df, "league", engine)

    # 3. For each league, pull users, rosters, matchups, drafts, transactions
    for lg in all_leagues:
        lid = lg["league_id"]
        name = lg["name"]
        season = lg["_season"]
        status = lg["status"]
        print(f"\n  [{season}] {name} ({lid}) - {status}")

        # Weeks with games to pull; only meaningful once the season is going.
        max_week = 18 if status == "complete" else 17

        # Users
        try:
            users = _get(f"{SLEEPER_BASE}/league/{lid}/users")
            for u in users or []:
                all_users.append({
                    "league_id": lid,
                    "user_id": u["user_id"],
                    "display_name": u.get("display_name", ""),
                    "avatar": u.get("avatar", ""),
                    "is_owner": bool(u.get("is_owner") or False),
                    "season": season,
                })
        except Exception as e:
            print(f"      users failed: {e}")

        # Rosters
        try:
            rosters = _get(f"{SLEEPER_BASE}/league/{lid}/rosters")
            for r in rosters or []:
                players = r.get("players", []) or []
                starters = r.get("starters", []) or []
                settings = r.get("settings", {}) or {}
                all_rosters.append({
                    "league_id": lid,
                    "roster_id": r["roster_id"],
                    "owner_id": r.get("owner_id", "") or "",
                    "players": str(players),
                    "starters": str(starters),
                    "wins": settings.get("wins", 0),
                    "losses": settings.get("losses", 0),
                    "ties": settings.get("ties", 0),
                    "fpts": settings.get("fpts", 0),
                    "fpts_decimal": settings.get("fpts_decimal", 0),
                    "fpts_against": settings.get("fpts_against", 0),
                    "fpts_against_decimal": settings.get("fpts_against_decimal", 0),
                    "season": season,
                })
        except Exception as e:
            print(f"      rosters failed: {e}")

        # Matchups (only for leagues that have played games)
        if status in ("in_season", "complete"):
            for week in range(1, max_week + 1):
                try:
                    matchups = _get(f"{SLEEPER_BASE}/league/{lid}/matchups/{week}")
                    if not matchups:
                        continue
                    for m in matchups:
                        all_matchups.append({
                            "league_id": lid,
                            "week": week,
                            "roster_id": m["roster_id"],
                            "matchup_id": m.get("matchup_id"),
                            "points": m.get("points", 0),
                            "starters_points": str(m.get("starters_points", [])),
                            "starters": str(m.get("starters", [])),
                            "players_points": str(m.get("players_points", {})),
                            "season": season,
                        })
                except Exception as e:
                    print(f"      Week {week} matchups failed: {e}")
                    break  # likely hit the end of the season

        # Draft picks
        try:
            drafts = _get(f"{SLEEPER_BASE}/league/{lid}/drafts")
        except Exception as e:
            drafts = []
            print(f"      drafts failed: {e}")
        for draft in drafts or []:
            draft_id = draft["draft_id"]
            try:
                picks = _get(f"{SLEEPER_BASE}/draft/{draft_id}/picks")
                for p in picks or []:
                    meta = p.get("metadata", {}) or {}
                    all_draft_picks.append({
                        "league_id": lid,
                        "draft_id": draft_id,
                        "round": p.get("round", 0),
                        "pick_no": p.get("pick_no", 0),
                        "player_id": p.get("player_id", ""),
                        "picked_by": p.get("picked_by", ""),
                        "roster_id": p.get("roster_id"),
                        "metadata_first_name": meta.get("first_name", ""),
                        "metadata_last_name": meta.get("last_name", ""),
                        "metadata_position": meta.get("position", ""),
                        "metadata_team": meta.get("team", ""),
                        "season": season,
                    })
            except Exception as e:
                print(f"      Draft {draft_id} picks failed: {e}")

        # Transactions (only for leagues that have played games)
        if status in ("in_season", "complete"):
            for week in range(1, max_week + 1):
                try:
                    txns = _get(f"{SLEEPER_BASE}/league/{lid}/transactions/{week}")
                    for t in txns or []:
                        all_transactions.append({
                            "league_id": lid,
                            "transaction_id": t.get("transaction_id", ""),
                            "type": t.get("type", ""),
                            "status": t.get("status", ""),
                            "week": week,
                            "adds": str(t.get("adds", {}) or {}),
                            "drops": str(t.get("drops", {}) or {}),
                            "roster_ids": str(t.get("roster_ids", [])),
                            "creator": t.get("creator", ""),
                            "created": t.get("created"),
                            "season": season,
                        })
                except Exception as e:
                    print(f"      Week {week} transactions failed: {e}")
                    break

    # Load all tables
    print("\n  Loading to SQL Server...")
    if all_users:
        _load_to_sleeper(pd.DataFrame(all_users), "user", engine)
    if all_rosters:
        _load_to_sleeper(pd.DataFrame(all_rosters), "roster", engine)
    if all_matchups:
        _load_to_sleeper(pd.DataFrame(all_matchups), "matchup", engine)
    if all_draft_picks:
        _load_to_sleeper(pd.DataFrame(all_draft_picks), "draft_pick", engine)
    if all_transactions:
        _load_to_sleeper(pd.DataFrame(all_transactions), "transaction", engine)

    # 4. Player ID mapping: the permanent bridge from Sleeper IDs to nflverse.
    print("\n  Building player ID map...")
    all_players = _get(f"{SLEEPER_BASE}/players/nfl")  # ~15K players, one blob

    player_rows = []
    for sleeper_id, pdata in all_players.items():
        # Only players in a fantasy-relevant context.
        if pdata.get("active") or pdata.get("team"):
            # Sleeper pads some gsis_ids with whitespace (" 00-0033873");
            # unstripped they would silently miss every nflverse join.
            gsis = pdata.get("gsis_id")
            gsis = str(gsis).strip() if gsis else None

            player_rows.append({
                "sleeper_id": sleeper_id,
                "gsis_id": gsis,
                "full_name": pdata.get("full_name", ""),
                "first_name": pdata.get("first_name", ""),
                "last_name": pdata.get("last_name", ""),
                "position": pdata.get("position", ""),
                "team": pdata.get("team", ""),
                "number": pdata.get("number"),
                "status": pdata.get("status", ""),
                "sport": pdata.get("sport", ""),
                "years_exp": pdata.get("years_exp"),
            })

    player_map_df = pd.DataFrame(player_rows)

    # Sleeper's own gsis_id field is sparse (~24% of drafted players). The
    # nflverse/DynastyProcess crosswalk maps sleeper_id -> gsis_id directly
    # and lifts drafted-player coverage above 90%; team DEFs have no GSIS by
    # nature and stay unmatched.
    native = int(player_map_df["gsis_id"].notna().sum())
    ids = nfl.load_ff_playerids().to_pandas()
    xwalk = ids[ids["sleeper_id"].notna() & ids["gsis_id"].notna()]
    xmap = dict(zip(
        xwalk["sleeper_id"].astype(float).astype(int).astype(str),
        xwalk["gsis_id"],
    ))
    player_map_df["gsis_source"] = player_map_df["gsis_id"].map(
        lambda v: "sleeper" if pd.notna(v) else None)
    fill = player_map_df["gsis_id"].isna() & player_map_df["sleeper_id"].isin(xmap)
    player_map_df.loc[fill, "gsis_id"] = player_map_df.loc[fill, "sleeper_id"].map(xmap)
    player_map_df.loc[fill, "gsis_source"] = "ff_playerids"

    _load_to_sleeper(player_map_df, "player_map", engine)

    has_gsis = int(player_map_df["gsis_id"].notna().sum())
    total = len(player_map_df)
    print(f"    Player map: {total:,} players, {has_gsis:,} with GSIS IDs "
          f"({100 * has_gsis / total:.1f}%) — {native:,} from Sleeper, "
          f"{has_gsis - native:,} filled from ff_playerids")

    print("\n  Sleeper ingestion complete!")


if __name__ == "__main__":
    ingest_sleeper()
