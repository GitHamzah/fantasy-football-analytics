"""Fantasy leaders and rankings endpoints."""

from fastapi import APIRouter, Query
from database import execute_query
from models import LeaderEntry

router = APIRouter(prefix="/leaders", tags=["Leaders"])


@router.get("/season", response_model=list[LeaderEntry])
def get_season_leaders(
    season: int = Query(..., description="Season year"),
    position: str | None = Query(None, description="Filter by position (QB, RB, WR, TE)"),
    scoring: str = Query("half_ppr", description="Scoring format: standard, half_ppr, ppr"),
    limit: int = Query(25, ge=1, le=100),
    season_type: str = Query("REG", description="REG or POST"),
):
    """Get top fantasy scorers for a season."""
    ppr_value = {"standard": 0.0, "half_ppr": 0.5, "ppr": 1.0}.get(scoring, 0.5)

    where = "WHERE f.season = :season AND f.season_type = :season_type"
    params = {"season": season, "season_type": season_type, "ppr": ppr_value, "limit": limit}

    if position:
        where += " AND f.position = :position"
        params["position"] = position.upper()

    rows = execute_query(f"""
        SELECT
            ROW_NUMBER() OVER (ORDER BY SUM(
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
            ) DESC)                         AS rank,
            f.gsis_id                       AS player_id,
            f.display_name                  AS player_name,
            f.position,
            f.recent_team                   AS team,
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
                                            AS fantasy_ppg
        FROM mart.fact_player_week f
        {where}
        GROUP BY f.gsis_id, f.display_name, f.position, f.recent_team
        ORDER BY fantasy_points DESC
        OFFSET 0 ROWS FETCH NEXT :limit ROWS ONLY
    """, params)

    return rows


@router.get("/weekly", response_model=list[LeaderEntry])
def get_weekly_leaders(
    season: int = Query(..., description="Season year"),
    week: int = Query(..., description="Week number"),
    position: str | None = Query(None, description="Filter by position"),
    scoring: str = Query("half_ppr", description="Scoring format"),
    limit: int = Query(25, ge=1, le=100),
):
    """Get top fantasy scorers for a specific week."""
    ppr_value = {"standard": 0.0, "half_ppr": 0.5, "ppr": 1.0}.get(scoring, 0.5)

    where = "WHERE f.season = :season AND f.week = :week"
    params = {"season": season, "week": week, "ppr": ppr_value, "limit": limit}

    if position:
        where += " AND f.position = :position"
        params["position"] = position.upper()

    rows = execute_query(f"""
        SELECT
            ROW_NUMBER() OVER (ORDER BY
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
            DESC)                           AS rank,
            f.gsis_id                       AS player_id,
            f.display_name                  AS player_name,
            f.position,
            f.recent_team                   AS team,
            1                               AS games_played,
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
            AS DECIMAL(10,2))               AS fantasy_ppg
        FROM mart.fact_player_week f
        {where}
        ORDER BY fantasy_points DESC
        OFFSET 0 ROWS FETCH NEXT :limit ROWS ONLY
    """, params)

    return rows
