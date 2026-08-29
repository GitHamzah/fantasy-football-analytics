"""Formation and personnel tendency endpoints.

Backed by mart.formation (team-season-formation-personnel_grouping grain).
Percentages are computed server-side in Python rather than with window
functions, keeping every query plain GROUP BY SQL that runs unchanged on both
SQL Server and Postgres.

Era caveat baked into the data: formation vocabulary is 7 values through 2022
(EMPTY, I_FORM, JUMBO, ...) and 3 values from 2023 (SHOTGUN, UNDER CENTER,
PISTOL). Cross-era comparisons compare labels, not football.
"""

from fastapi import APIRouter, HTTPException, Query
from database import execute_query

router = APIRouter(prefix="/advanced", tags=["Formations"])


def _personnel_label(grouping: str) -> str:
    """Expand a grouping code into a human label.

    First digit is RB count, second is TE count; WR is implied as the rest of
    the five skill spots. Jumbo sets (extra OL eating a skill spot) can push
    the implied WR below zero, so it clamps at 0.
    """
    rb, te = int(grouping[0]), int(grouping[1])
    wr = max(0, 5 - rb - te)
    return f"{rb} RB, {te} TE, {wr} WR"


def _pct(part: float, whole: float) -> float:
    return round(100.0 * part / whole, 1) if whole else 0.0


@router.get("/formations")
def get_team_formations(
    season: int = Query(..., description="Season year"),
    team: str = Query(..., description="Team abbreviation, e.g. KC"),
):
    """Formation and personnel tendencies for one team in one season."""
    team = team.upper()

    formations = execute_query("""
        SELECT
            f.formation,
            SUM(f.play_count) AS play_count,
            SUM(CASE WHEN f.avg_defenders_in_box IS NOT NULL
                     THEN f.avg_defenders_in_box * f.play_count END)
              / NULLIF(SUM(CASE WHEN f.avg_defenders_in_box IS NOT NULL
                                THEN f.play_count END), 0) AS avg_box
        FROM mart.formation f
        WHERE f.season = :season AND f.team = :team
        GROUP BY f.formation
        ORDER BY SUM(f.play_count) DESC
    """, {"season": season, "team": team})

    if not formations:
        raise HTTPException(404, f"No formation data for {team} in {season}")

    total_plays = sum(r["play_count"] for r in formations)

    personnel = execute_query("""
        SELECT
            f.personnel_grouping,
            SUM(f.play_count) AS play_count
        FROM mart.formation f
        WHERE f.season = :season AND f.team = :team
          AND f.personnel_grouping IS NOT NULL
        GROUP BY f.personnel_grouping
        ORDER BY SUM(f.play_count) DESC
    """, {"season": season, "team": team})

    return {
        "team": team,
        "season": season,
        "total_plays": total_plays,
        "formations": [
            {
                "formation": r["formation"],
                "play_count": r["play_count"],
                "pct": _pct(r["play_count"], total_plays),
                "avg_box": round(r["avg_box"], 1) if r["avg_box"] is not None else None,
            }
            for r in formations
        ],
        # Percentages share the total_plays denominator, so the personnel list
        # sums slightly under 100 — the gap is plays whose 2023+ personnel
        # string failed offense validation in staging.
        "personnel": [
            {
                "grouping": r["personnel_grouping"],
                "label": _personnel_label(r["personnel_grouping"]),
                "play_count": r["play_count"],
                "pct": _pct(r["play_count"], total_plays),
            }
            for r in personnel
        ],
    }


@router.get("/formations/league")
def get_league_formations(
    season: int = Query(..., description="Season year"),
):
    """Every team's formation split for a season, sorted by shotgun rate.

    Compact by design — one row per team for the league-wide comparison view.
    Formation percentages use each team's total plays; top_personnel is the
    team's most-run parsed grouping.
    """
    rows = execute_query("""
        SELECT
            f.team,
            f.formation,
            SUM(f.play_count) AS play_count
        FROM mart.formation f
        WHERE f.season = :season
        GROUP BY f.team, f.formation
    """, {"season": season})

    if not rows:
        raise HTTPException(404, f"No formation data for season {season}")

    top_personnel = execute_query("""
        SELECT
            f.team,
            f.personnel_grouping,
            SUM(f.play_count) AS play_count
        FROM mart.formation f
        WHERE f.season = :season AND f.personnel_grouping IS NOT NULL
        GROUP BY f.team, f.personnel_grouping
    """, {"season": season})

    teams: dict[str, dict] = {}
    for r in rows:
        t = teams.setdefault(r["team"], {"total": 0, "formations": {}})
        t["total"] += r["play_count"]
        t["formations"][r["formation"]] = r["play_count"]

    best: dict[str, dict] = {}
    for r in top_personnel:
        cur = best.get(r["team"])
        if cur is None or r["play_count"] > cur["play_count"]:
            best[r["team"]] = r

    result = []
    for team, t in teams.items():
        top = best.get(team)
        result.append({
            "team": team,
            "total_plays": t["total"],
            "shotgun_pct": _pct(t["formations"].get("SHOTGUN", 0), t["total"]),
            "under_center_pct": _pct(t["formations"].get("UNDER CENTER", 0), t["total"]),
            "pistol_pct": _pct(t["formations"].get("PISTOL", 0), t["total"]),
            "top_personnel": top["personnel_grouping"] if top else None,
            "top_personnel_label": _personnel_label(top["personnel_grouping"]) if top else None,
        })

    result.sort(key=lambda r: r["shotgun_pct"], reverse=True)
    return {"season": season, "teams": result}


# Positions surfaced in the formation visual, with how many of each to return.
_ROSTER_SLOTS = {"QB": 1, "RB": 2, "WR": 4, "TE": 2}


@router.get("/formations/roster")
def get_formation_roster(
    team: str = Query(..., description="Team abbreviation, e.g. KC"),
    season: int = Query(..., description="Season year"),
):
    """The players who populate the formation visual for a team-season.

    Ranked by regular-season games played for that team, with total touches
    plus targets as the tiebreak so the actual starters outrank rotational
    players with equal game counts. OL is intentionally empty — participation
    data carries no per-player OL usage.
    """
    team = team.upper()

    rows = execute_query("""
        SELECT
            f.gsis_id                                   AS player_id,
            COALESCE(d.display_name, f.display_name)    AS name,
            f.position,
            COUNT(DISTINCT f.week)                      AS games,
            SUM(COALESCE(f.attempts, 0)
              + COALESCE(f.carries, 0)
              + COALESCE(f.targets, 0))                 AS touches
        FROM mart.fact_player_week f
        LEFT JOIN mart.dim_player d ON d.gsis_id = f.gsis_id
        WHERE f.season = :season
          AND f.recent_team = :team
          AND f.season_type = 'REG'
          AND f.position IN ('QB', 'RB', 'WR', 'TE')
        GROUP BY f.gsis_id, COALESCE(d.display_name, f.display_name), f.position
        ORDER BY f.position, COUNT(DISTINCT f.week) DESC
    """, {"season": season, "team": team})

    if not rows:
        raise HTTPException(404, f"No roster data for {team} in {season}")

    players: dict[str, list] = {pos: [] for pos in _ROSTER_SLOTS}
    by_pos: dict[str, list] = {}
    for r in rows:
        by_pos.setdefault(r["position"], []).append(r)

    for pos, limit in _ROSTER_SLOTS.items():
        ranked = sorted(
            by_pos.get(pos, []),
            key=lambda r: (r["games"], r["touches"]),
            reverse=True,
        )
        players[pos] = [
            {"name": r["name"], "player_id": r["player_id"]}
            for r in ranked[:limit]
        ]

    players["OL"] = []

    return {"team": team, "season": season, "players": players}
