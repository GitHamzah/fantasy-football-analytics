"""Player statistics endpoints — season and weekly granularity."""

from fastapi import APIRouter, Query, HTTPException
from database import execute_query
from models import PlayerSeasonStats, PlayerWeekStats

router = APIRouter(prefix="/stats", tags=["Stats"])


@router.get("/season/{player_id}", response_model=list[PlayerSeasonStats])
def get_player_season_stats(
    player_id: str,
    season: int | None = Query(None, description="Filter to a specific season"),
    scoring: str = Query("half_ppr", description="Scoring format: standard, half_ppr, ppr"),
):
    """Get aggregated season stats for a player."""
    ppr_value = {"standard": 0.0, "half_ppr": 0.5, "ppr": 1.0}.get(scoring, 0.5)

    where = "WHERE f.gsis_id = :player_id"
    params = {"player_id": player_id, "ppr": ppr_value}

    if season:
        where += " AND f.season = :season"
        params["season"] = season

    rows = execute_query(f"""
        SELECT
            f.gsis_id                       AS player_id,
            f.display_name                  AS player_name,
            f.position,
            f.recent_team                   AS team,
            f.season,
            COUNT(*)                        AS games_played,
            CAST(SUM(
                ISNULL(f.passing_yards, 0) * 0.04
              + ISNULL(f.passing_tds, 0) * 4.0
              + ISNULL(f.interceptions, 0) * -2.0
              + ISNULL(f.rushing_yards, 0) * 0.1
              + ISNULL(f.rushing_tds, 0) * 6.0
              + ISNULL(f.receptions, 0) * :ppr
              + ISNULL(f.receiving_yards, 0) * 0.1
              + ISNULL(f.receiving_tds, 0) * 6.0
              + ISNULL(f.total_fumbles_lost, 0) * -2.0
              + ISNULL(f.total_2pt_conversions, 0) * 2.0
              + ISNULL(f.special_teams_tds, 0) * 6.0
            ) AS DECIMAL(10,2))             AS fantasy_points,
            CAST(SUM(
                ISNULL(f.passing_yards, 0) * 0.04
              + ISNULL(f.passing_tds, 0) * 4.0
              + ISNULL(f.interceptions, 0) * -2.0
              + ISNULL(f.rushing_yards, 0) * 0.1
              + ISNULL(f.rushing_tds, 0) * 6.0
              + ISNULL(f.receptions, 0) * :ppr
              + ISNULL(f.receiving_yards, 0) * 0.1
              + ISNULL(f.receiving_tds, 0) * 6.0
              + ISNULL(f.total_fumbles_lost, 0) * -2.0
              + ISNULL(f.total_2pt_conversions, 0) * 2.0
              + ISNULL(f.special_teams_tds, 0) * 6.0
            ) / NULLIF(COUNT(*), 0) AS DECIMAL(10,2))
                                            AS fantasy_ppg,
            CAST(SUM(ISNULL(f.passing_yards, 0)) AS DECIMAL(10,1))  AS passing_yards,
            SUM(ISNULL(f.passing_tds, 0))   AS passing_tds,
            SUM(ISNULL(f.interceptions, 0)) AS interceptions,
            CAST(SUM(ISNULL(f.rushing_yards, 0)) AS DECIMAL(10,1))  AS rushing_yards,
            SUM(ISNULL(f.rushing_tds, 0))   AS rushing_tds,
            SUM(ISNULL(f.receptions, 0))    AS receptions,
            SUM(ISNULL(f.targets, 0))       AS targets,
            CAST(SUM(ISNULL(f.receiving_yards, 0)) AS DECIMAL(10,1)) AS receiving_yards,
            SUM(ISNULL(f.receiving_tds, 0)) AS receiving_tds,
            SUM(ISNULL(f.total_fumbles_lost, 0)) AS total_fumbles_lost
        FROM mart.fact_player_week f
        {where}
        GROUP BY f.gsis_id, f.display_name, f.position, f.recent_team, f.season
        ORDER BY f.season DESC
    """, params)

    if not rows:
        raise HTTPException(status_code=404, detail="No stats found for this player")
    return rows


@router.get("/weekly/{player_id}", response_model=list[PlayerWeekStats])
def get_player_weekly_stats(
    player_id: str,
    season: int = Query(..., description="Season year"),
    scoring: str = Query("half_ppr", description="Scoring format: standard, half_ppr, ppr"),
):
    """Get week-by-week stats for a player in a given season."""
    ppr_value = {"standard": 0.0, "half_ppr": 0.5, "ppr": 1.0}.get(scoring, 0.5)

    rows = execute_query("""
        SELECT
            f.gsis_id                       AS player_id,
            f.display_name                  AS player_name,
            f.position,
            f.recent_team                   AS team,
            f.season,
            f.week,
            f.opponent_team                 AS opponent,
            CAST(
                ISNULL(f.passing_yards, 0) * 0.04
              + ISNULL(f.passing_tds, 0) * 4.0
              + ISNULL(f.interceptions, 0) * -2.0
              + ISNULL(f.rushing_yards, 0) * 0.1
              + ISNULL(f.rushing_tds, 0) * 6.0
              + ISNULL(f.receptions, 0) * :ppr
              + ISNULL(f.receiving_yards, 0) * 0.1
              + ISNULL(f.receiving_tds, 0) * 6.0
              + ISNULL(f.total_fumbles_lost, 0) * -2.0
              + ISNULL(f.total_2pt_conversions, 0) * 2.0
              + ISNULL(f.special_teams_tds, 0) * 6.0
            AS DECIMAL(10,2))               AS fantasy_points,
            ISNULL(f.passing_yards, 0)      AS passing_yards,
            ISNULL(f.passing_tds, 0)        AS passing_tds,
            ISNULL(f.interceptions, 0)      AS interceptions,
            ISNULL(f.rushing_yards, 0)      AS rushing_yards,
            ISNULL(f.rushing_tds, 0)        AS rushing_tds,
            ISNULL(f.receptions, 0)         AS receptions,
            ISNULL(f.targets, 0)            AS targets,
            ISNULL(f.receiving_yards, 0)    AS receiving_yards,
            ISNULL(f.receiving_tds, 0)      AS receiving_tds
        FROM mart.fact_player_week f
        WHERE f.gsis_id = :player_id
          AND f.season = :season
        ORDER BY f.week
    """, {"player_id": player_id, "season": season, "ppr": ppr_value})

    if not rows:
        raise HTTPException(status_code=404, detail="No stats found")
    return rows
