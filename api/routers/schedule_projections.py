"""Scheme-adjusted schedule projections: 2025 per-shell production weighted by
each 2026 opponent's coverage-shell tendencies.

Reads mart.season_projection and mart.schedule_projection (both synced to
Neon), plus mart.def_formation for the opponent tendency breakdowns. Every
numeric is cast to int/float — psycopg2 returns Decimal for aggregates.
"""

from fastapi import APIRouter, HTTPException, Query
from database import execute_query

router = APIRouter(prefix="/projections", tags=["Schedule Projections"])


def _f(v, digits=2):
    return round(float(v), digits) if v is not None else None


def _rating(score) -> str:
    if score is None:
        return "Unknown"
    s = float(score)
    if s > 1.1:
        return "Smash"
    if s > 1.0:
        return "Favorable"
    if s > 0.9:
        return "Neutral"
    if s > 0.8:
        return "Tough"
    return "Avoid"


@router.get("/schedule-adjusted")
def get_schedule_adjusted(
    season: int = Query(2026, description="Projection season"),
    position: str | None = Query(None, description="QB, RB, WR or TE"),
    limit: int = Query(20, ge=1, le=500),
):
    """Season-total scheme-adjusted projections, best schedules first."""
    if season != 2026:
        raise HTTPException(404, "Scheme-adjusted projections exist for 2026 only")

    where = ""
    params: dict = {}
    if position:
        where = "WHERE p.position = :position"
        params["position"] = position.upper()

    rows = execute_query(f"""
        SELECT
            p.player_id,
            p.player_name,
            p.position,
            p.team,
            p.projected_games,
            p.ppg_2025,
            p.targets_pg,
            p.carries_pg,
            p.avg_projected_yards,
            p.total_projected_yards,
            p.total_projected_tds,
            p.avg_epa,
            p.avg_matchup_score
        FROM mart.season_projection p
        {where}
        ORDER BY p.total_projected_yards DESC
    """, params)

    if not rows:
        raise HTTPException(404, f"No projections for position {position}")

    return {
        "season": season,
        "position": position.upper() if position else None,
        "players": [
            {
                "player_id": r["player_id"],
                "player_name": r["player_name"],
                "position": r["position"],
                "team": r["team"],
                "projected_games": int(r["projected_games"]),
                "ppg_2025": _f(r["ppg_2025"], 1),
                "targets_pg": _f(r["targets_pg"], 1),
                "carries_pg": _f(r["carries_pg"], 1),
                "avg_projected_yards": _f(r["avg_projected_yards"], 1),
                "total_projected_yards": _f(r["total_projected_yards"], 0),
                "total_projected_tds": _f(r["total_projected_tds"], 1),
                "avg_epa": _f(r["avg_epa"], 3),
                "avg_matchup_score": _f(r["avg_matchup_score"], 3),
                "schedule_rating": _rating(r["avg_matchup_score"]),
            }
            for r in rows[:limit]
        ],
    }


@router.get("/weekly-matchup")
def get_weekly_matchup(
    player_id: str = Query(..., description="GSIS player id"),
    season: int = Query(2026, description="Projection season"),
):
    """One player's week-by-week scheme-adjusted projection with the opponent
    shell mix behind each number, plus the three best and worst weeks."""
    if season != 2026:
        raise HTTPException(404, "Scheme-adjusted projections exist for 2026 only")

    weeks = execute_query("""
        SELECT
            p.player_name,
            p.position,
            p.team,
            p.week,
            p.opponent,
            p.projected_yards,
            p.projected_tds,
            p.weighted_epa,
            p.matchup_score
        FROM mart.schedule_projection p
        WHERE p.player_id = :pid
        ORDER BY p.week
    """, {"pid": player_id})

    if not weeks:
        raise HTTPException(404, f"No schedule projection for player {player_id}")

    # Opponent shell mixes (2025 tendencies) for every defense this player sees.
    tendencies = execute_query("""
        SELECT
            f.team,
            f.coverage_shell,
            SUM(f.play_count) AS plays
        FROM mart.def_formation f
        WHERE f.season = 2025 AND f.coverage_shell IS NOT NULL
        GROUP BY f.team, f.coverage_shell
    """)
    mix: dict[str, dict[str, float]] = {}
    totals: dict[str, int] = {}
    for t in tendencies:
        totals[t["team"]] = totals.get(t["team"], 0) + int(t["plays"])
    for t in tendencies:
        mix.setdefault(t["team"], {})[t["coverage_shell"]] = round(
            100.0 * int(t["plays"]) / totals[t["team"]], 1
        )

    week_rows = [
        {
            "week": int(w["week"]),
            "opponent": w["opponent"],
            "projected_yards": _f(w["projected_yards"], 1),
            "projected_tds": _f(w["projected_tds"], 2),
            "weighted_epa": _f(w["weighted_epa"], 3),
            "matchup_score": _f(w["matchup_score"], 3),
            "matchup_rating": _rating(w["matchup_score"]),
            "opponent_shell_tendencies": mix.get(w["opponent"], {}),
        }
        for w in weeks
    ]

    ranked = sorted(
        (w for w in week_rows if w["matchup_score"] is not None),
        key=lambda w: w["matchup_score"],
        reverse=True,
    )
    pick = lambda ws: [
        {"week": w["week"], "opponent": w["opponent"], "score": w["matchup_score"]}
        for w in ws
    ]

    return {
        "player_id": player_id,
        "player_name": weeks[0]["player_name"],
        "position": weeks[0]["position"],
        "team": weeks[0]["team"],
        "season": season,
        "weeks": week_rows,
        "best_weeks": pick(ranked[:3]),
        "worst_weeks": pick(list(reversed(ranked[-3:]))),
    }
