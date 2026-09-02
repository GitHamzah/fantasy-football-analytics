"""My League endpoints: Hamzah's Sleeper leagues joined to the analytics engine.

Everything reads the three synced marts (league_standings, my_roster,
league_matchup) rather than the sleeper schema, because only mart tables ship
to Neon — the raw Sleeper tables exist on SQL Server alone. All numerics are
cast to int/float (psycopg2 returns Decimal for aggregates and the fpts math).
"""

from fastapi import APIRouter, HTTPException, Query
from database import execute_query

router = APIRouter(prefix="/leagues", tags=["My Leagues"])

# Hamzah's Sleeper user id; every "my_*"/"is_me" field keys off it.
MY_USER_ID = "997944313776496640"


def _f(v, digits=2):
    return round(float(v), digits) if v is not None else None


@router.get("")
def get_my_leagues(
    season: int = Query(2026, description="Season year"),
):
    """All of Hamzah's leagues for a season, with his record and standing."""
    rows = execute_query("""
        SELECT
            s.league_id,
            s.league_name,
            s.season,
            s.status,
            s.scoring_type,
            s.total_rosters,
            s.wins,
            s.losses,
            s.ties,
            s.total_points,
            s.standing
        FROM mart.league_standings s
        WHERE s.season = :season AND s.user_id = :uid
        ORDER BY s.league_name
    """, {"season": season, "uid": MY_USER_ID})

    if not rows:
        raise HTTPException(404, f"No leagues found for season {season}")

    return {
        "user_id": MY_USER_ID,
        "season": season,
        "leagues": [
            {
                "league_id": r["league_id"],
                "name": r["league_name"],
                "status": r["status"],
                "total_rosters": int(r["total_rosters"]),
                "scoring_type": r["scoring_type"],
                "my_record": f"{int(r['wins'])}-{int(r['losses'])}"
                             + (f"-{int(r['ties'])}" if int(r["ties"]) else ""),
                "my_points": _f(r["total_points"], 1),
                "my_standing": int(r["standing"]),
            }
            for r in rows
        ],
    }


@router.get("/{league_id}/roster")
def get_my_league_roster(league_id: str):
    """Hamzah's roster in one league, with 2025 production and shell matchups."""
    rows = execute_query("""
        SELECT
            m.league_id,
            m.league_name,
            m.manager_name,
            m.player_name,
            m.position,
            m.team,
            m.is_starter,
            m.gsis_id,
            m.sleeper_id,
            m.ppg,
            m.games_played,
            m.total_yards,
            m.total_tds,
            m.best_shell,
            m.best_shell_avg_yards,
            m.worst_shell,
            m.worst_shell_avg_yards
        FROM mart.my_roster m
        WHERE m.league_id = :lid
        ORDER BY m.is_starter DESC, m.ppg DESC
    """, {"lid": league_id})

    if not rows:
        raise HTTPException(404, f"No roster found in league {league_id}")

    record = execute_query("""
        SELECT s.wins, s.losses, s.ties
        FROM mart.league_standings s
        WHERE s.league_id = :lid AND s.user_id = :uid
    """, {"lid": league_id, "uid": MY_USER_ID})
    rec = record[0] if record else None

    return {
        "league_id": league_id,
        "league_name": rows[0]["league_name"],
        "manager": rows[0]["manager_name"],
        "record": (
            f"{int(rec['wins'])}-{int(rec['losses'])}"
            + (f"-{int(rec['ties'])}" if int(rec["ties"]) else "")
            if rec else None
        ),
        "players": [
            {
                "player_name": r["player_name"],
                "position": r["position"],
                "team": r["team"],
                "is_starter": bool(r["is_starter"]),
                "gsis_id": r["gsis_id"],
                "sleeper_id": r["sleeper_id"],
                "ppg_2025": _f(r["ppg"], 1),
                "games_2025": int(r["games_played"]) if r["games_played"] is not None else None,
                "yards_2025": _f(r["total_yards"], 0),
                "tds_2025": int(r["total_tds"]) if r["total_tds"] is not None else None,
                "best_matchup": (
                    {"shell": r["best_shell"], "avg_yards": _f(r["best_shell_avg_yards"], 1)}
                    if r["best_shell"] else None
                ),
                "worst_matchup": (
                    {"shell": r["worst_shell"], "avg_yards": _f(r["worst_shell_avg_yards"], 1)}
                    if r["worst_shell"] else None
                ),
            }
            for r in rows
        ],
    }


@router.get("/{league_id}/standings")
def get_league_standings(league_id: str):
    """Full standings for one league."""
    rows = execute_query("""
        SELECT
            s.league_name,
            s.season,
            s.standing,
            s.manager_name,
            s.user_id,
            s.wins,
            s.losses,
            s.ties,
            s.total_points,
            s.total_points_against
        FROM mart.league_standings s
        WHERE s.league_id = :lid
        ORDER BY s.standing
    """, {"lid": league_id})

    if not rows:
        raise HTTPException(404, f"No standings found for league {league_id}")

    return {
        "league_id": league_id,
        "league_name": rows[0]["league_name"],
        "season": int(rows[0]["season"]),
        "standings": [
            {
                "rank": int(r["standing"]),
                "manager": r["manager_name"],
                "wins": int(r["wins"]),
                "losses": int(r["losses"]),
                "ties": int(r["ties"]),
                "points": _f(r["total_points"], 1),
                "points_against": _f(r["total_points_against"], 1),
                "is_me": r["user_id"] == MY_USER_ID,
            }
            for r in rows
        ],
    }


@router.get("/{league_id}/matchups")
def get_league_matchups(
    league_id: str,
    week: int = Query(1, ge=1, le=18),
):
    """One week's head-to-head matchups in a league."""
    rows = execute_query("""
        SELECT
            m.matchup_id,
            m.roster_id,
            m.points,
            m.manager_name,
            m.user_id
        FROM mart.league_matchup m
        WHERE m.league_id = :lid AND m.week = :week
        ORDER BY m.matchup_id, m.roster_id
    """, {"lid": league_id, "week": week})

    if not rows:
        raise HTTPException(404, f"No matchups for league {league_id} week {week}")

    games: dict = {}
    for r in rows:
        mid = r["matchup_id"]
        games.setdefault(mid, []).append({
            "roster_id": int(r["roster_id"]),
            "manager": r["manager_name"],
            "points": _f(r["points"], 2),
            "is_me": r["user_id"] == MY_USER_ID,
        })

    return {
        "league_id": league_id,
        "week": week,
        "matchups": [
            {"matchup_id": int(mid) if mid is not None else None, "teams": teams}
            for mid, teams in sorted(
                games.items(), key=lambda kv: (kv[0] is None, kv[0])
            )
        ],
    }
