"""Advanced fantasy analytics endpoints."""

from fastapi import APIRouter, Query
from database import execute_query

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/consistency")
def get_consistency_rankings(
    season: int = Query(..., description="Season year"),
    position: str | None = Query(None, description="Filter by position"),
    scoring: str = Query("half_ppr", description="standard, half_ppr, ppr"),
    limit: int = Query(50, ge=1, le=100),
    min_games: int = Query(8, description="Minimum games to qualify"),
):
    """Player consistency rankings with boom/bust rates and floor/ceiling."""
    ppr_value = {"standard": 0.0, "half_ppr": 0.5, "ppr": 1.0}.get(scoring, 0.5)

    where = "WHERE f.season = :season AND f.season_type = 'REG'"
    params = {"season": season, "ppr": ppr_value, "limit": limit, "min_games": min_games}

    if position:
        where += " AND f.position = :position"
        params["position"] = position.upper()

    rows = execute_query(f"""
        WITH player_weeks AS (
            SELECT
                f.gsis_id,
                f.display_name,
                f.position,
                f.recent_team,
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
                AS DECIMAL(10,2)) AS week_pts
            FROM mart.fact_player_week f
            {where}
        )
        SELECT
            pw.gsis_id                                  AS player_id,
            pw.display_name                             AS player_name,
            pw.position,
            pw.recent_team                              AS team,
            COUNT(*)                                    AS games_played,
            CAST(SUM(pw.week_pts) AS DECIMAL(10,1))     AS total_points,
            CAST(AVG(pw.week_pts) AS DECIMAL(10,1))     AS ppg,
            CAST(STDEV(pw.week_pts) AS DECIMAL(10,1))   AS std_dev,
            CAST(MIN(pw.week_pts) AS DECIMAL(10,1))     AS floor,
            CAST(MAX(pw.week_pts) AS DECIMAL(10,1))     AS ceiling,
            SUM(CASE WHEN pw.week_pts >= 20 THEN 1 ELSE 0 END) AS boom_weeks,
            SUM(CASE WHEN pw.week_pts < 8 THEN 1 ELSE 0 END)   AS bust_weeks,
            CAST(SUM(CASE WHEN pw.week_pts >= 20 THEN 1.0 ELSE 0 END)
                / COUNT(*) * 100 AS DECIMAL(5,1))       AS boom_pct,
            CAST(SUM(CASE WHEN pw.week_pts < 8 THEN 1.0 ELSE 0 END)
                / COUNT(*) * 100 AS DECIMAL(5,1))       AS bust_pct,
            CAST(AVG(pw.week_pts) / NULLIF(STDEV(pw.week_pts), 0)
                AS DECIMAL(10,2))                       AS consistency_score
        FROM player_weeks pw
        GROUP BY pw.gsis_id, pw.display_name, pw.position, pw.recent_team
        HAVING COUNT(*) >= :min_games
        ORDER BY consistency_score DESC
        OFFSET 0 ROWS FETCH NEXT :limit ROWS ONLY
    """, params)

    return rows


@router.get("/vor")
def get_value_over_replacement(
    season: int = Query(..., description="Season year"),
    scoring: str = Query("half_ppr", description="standard, half_ppr, ppr"),
    qb_baseline: int = Query(12, description="QB baseline rank"),
    rb_baseline: int = Query(24, description="RB baseline rank"),
    wr_baseline: int = Query(24, description="WR baseline rank"),
    te_baseline: int = Query(12, description="TE baseline rank"),
    limit: int = Query(75, ge=1, le=200),
    min_games: int = Query(8, description="Minimum games to qualify"),
):
    """Value Over Replacement Player rankings.

    Calculates how many PPG each player scores above the 'replacement level'
    player at their position. This is the core draft value metric.
    """
    ppr_value = {"standard": 0.0, "half_ppr": 0.5, "ppr": 1.0}.get(scoring, 0.5)

    rows = execute_query("""
        WITH player_totals AS (
            SELECT
                f.gsis_id,
                f.display_name,
                f.position,
                f.recent_team,
                COUNT(*) AS games,
                CAST(AVG(
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
                ) AS DECIMAL(10,2)) AS ppg,
                ROW_NUMBER() OVER (
                    PARTITION BY f.position
                    ORDER BY AVG(
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
                    ) DESC
                ) AS pos_rank
            FROM mart.fact_player_week f
            WHERE f.season = :season
              AND f.season_type = 'REG'
              AND f.position IN ('QB', 'RB', 'WR', 'TE')
            GROUP BY f.gsis_id, f.display_name, f.position, f.recent_team
            HAVING COUNT(*) >= :min_games
        ),
        baselines AS (
            SELECT 'QB' AS position, ppg AS baseline_ppg FROM player_totals WHERE position = 'QB' AND pos_rank = :qb_base
            UNION ALL
            SELECT 'RB', ppg FROM player_totals WHERE position = 'RB' AND pos_rank = :rb_base
            UNION ALL
            SELECT 'WR', ppg FROM player_totals WHERE position = 'WR' AND pos_rank = :wr_base
            UNION ALL
            SELECT 'TE', ppg FROM player_totals WHERE position = 'TE' AND pos_rank = :te_base
        )
        SELECT TOP (:limit)
            pt.gsis_id                                      AS player_id,
            pt.display_name                                 AS player_name,
            pt.position,
            pt.recent_team                                  AS team,
            pt.games                                        AS games_played,
            pt.pos_rank,
            pt.ppg,
            CAST(b.baseline_ppg AS DECIMAL(10,1))           AS baseline_ppg,
            CAST(pt.ppg - b.baseline_ppg AS DECIMAL(10,1))  AS vor_ppg,
            CAST((pt.ppg - b.baseline_ppg) * pt.games AS DECIMAL(10,1)) AS vor_total
        FROM player_totals pt
        JOIN baselines b ON pt.position = b.position
        ORDER BY vor_ppg DESC
    """, {
        "season": season,
        "ppr": ppr_value,
        "min_games": min_games,
        "qb_base": qb_baseline,
        "rb_base": rb_baseline,
        "wr_base": wr_baseline,
        "te_base": te_baseline,
        "limit": limit,
    })

    return rows


@router.get("/opportunity")
def get_opportunity_vs_production(
    season: int = Query(..., description="Season year"),
    position: str | None = Query(None, description="Filter by position"),
    scoring: str = Query("half_ppr", description="standard, half_ppr, ppr"),
    min_games: int = Query(8, description="Minimum games to qualify"),
    limit: int = Query(75, ge=1, le=200),
):
    """Opportunity (targets, carries) vs fantasy production scatter data.

    Players above the trendline are efficient. Players below with high
    opportunity are regression candidates (buy low targets).
    """
    ppr_value = {"standard": 0.0, "half_ppr": 0.5, "ppr": 1.0}.get(scoring, 0.5)

    where = "WHERE f.season = :season AND f.season_type = 'REG' AND f.position IN ('RB', 'WR', 'TE')"
    params = {"season": season, "ppr": ppr_value, "min_games": min_games, "limit": limit}

    if position:
        where = "WHERE f.season = :season AND f.season_type = 'REG' AND f.position = :position"
        params["position"] = position.upper()

    rows = execute_query(f"""
        SELECT TOP (:limit)
            f.gsis_id                                   AS player_id,
            f.display_name                              AS player_name,
            f.position,
            f.recent_team                               AS team,
            COUNT(*)                                    AS games_played,
            CAST(AVG(ISNULL(f.targets, 0) + ISNULL(f.carries, 0))
                AS DECIMAL(10,1))                       AS opportunities_pg,
            CAST(AVG(ISNULL(f.targets, 0))
                AS DECIMAL(10,1))                       AS targets_pg,
            CAST(AVG(ISNULL(f.carries, 0))
                AS DECIMAL(10,1))                       AS carries_pg,
            CAST(AVG(
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
            ) AS DECIMAL(10,1))                         AS fantasy_ppg,
            CAST(AVG(CAST(ISNULL(f.target_share, 0) AS FLOAT))
                * 100 AS DECIMAL(5,1))                  AS target_share_pct,
            CAST(AVG(CAST(ISNULL(f.air_yards_share, 0) AS FLOAT))
                * 100 AS DECIMAL(5,1))                  AS air_yards_share_pct,
            CAST(AVG(CAST(ISNULL(f.wopr, 0) AS FLOAT))
                AS DECIMAL(6,3))                        AS wopr
        FROM mart.fact_player_week f
        {where}
        GROUP BY f.gsis_id, f.display_name, f.position, f.recent_team
        HAVING COUNT(*) >= :min_games
        ORDER BY opportunities_pg DESC
    """, params)

    return rows


@router.get("/defense")
def get_defensive_rankings(
    season: int = Query(..., description="Season year"),
    scoring: str = Query("half_ppr", description="standard, half_ppr, ppr"),
):
    """Fantasy points allowed by defense, broken down by position.

    Shows which defenses are easiest/hardest matchups for each position.
    """
    ppr_value = {"standard": 0.0, "half_ppr": 0.5, "ppr": 1.0}.get(scoring, 0.5)

    rows = execute_query("""
        SELECT
            f.opponent_team                             AS defense,
            f.position,
            COUNT(DISTINCT CONCAT(f.season, '-', f.week)) AS games,
            CAST(AVG(
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
            ) AS DECIMAL(10,1))                         AS avg_pts_allowed,
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
            ) AS DECIMAL(10,1))                         AS total_pts_allowed
        FROM mart.fact_player_week f
        WHERE f.season = :season
          AND f.season_type = 'REG'
          AND f.position IN ('QB', 'RB', 'WR', 'TE')
        GROUP BY f.opponent_team, f.position
        ORDER BY f.position, avg_pts_allowed DESC
    """, {"season": season, "ppr": ppr_value})

    return rows


@router.get("/trajectory/{player_id}")
def get_player_trajectory(
    player_id: str,
    scoring: str = Query("half_ppr", description="standard, half_ppr, ppr"),
):
    """Multi-season career trajectory for a player.

    Shows PPG, total points, and games across all available seasons.
    """
    ppr_value = {"standard": 0.0, "half_ppr": 0.5, "ppr": 1.0}.get(scoring, 0.5)

    rows = execute_query("""
        SELECT
            f.gsis_id                                   AS player_id,
            f.display_name                              AS player_name,
            f.position,
            f.recent_team                               AS team,
            f.season,
            COUNT(*)                                    AS games_played,
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
            ) AS DECIMAL(10,1))                         AS total_points,
            CAST(AVG(
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
            ) AS DECIMAL(10,1))                         AS ppg,
            CAST(AVG(ISNULL(f.targets, 0) + ISNULL(f.carries, 0))
                AS DECIMAL(10,1))                       AS opportunities_pg,
            CAST(AVG(ISNULL(f.targets, 0))
                AS DECIMAL(10,1))                       AS targets_pg,
            CAST(AVG(ISNULL(f.carries, 0))
                AS DECIMAL(10,1))                       AS carries_pg
        FROM mart.fact_player_week f
        WHERE f.gsis_id = :player_id
          AND f.season_type = 'REG'
        GROUP BY f.gsis_id, f.display_name, f.position, f.recent_team, f.season
        ORDER BY f.season
    """, {"player_id": player_id, "ppr": ppr_value})

    return rows


@router.get("/compare")
def compare_players(
    player_ids: str = Query(..., description="Comma-separated player IDs (2-4 players)"),
    season: int = Query(..., description="Season year"),
    scoring: str = Query("half_ppr", description="standard, half_ppr, ppr"),
):
    """Side-by-side comparison of 2-4 players for sit/start decisions."""
    ppr_value = {"standard": 0.0, "half_ppr": 0.5, "ppr": 1.0}.get(scoring, 0.5)

    ids = [pid.strip() for pid in player_ids.split(",")][:4]
    placeholders = ",".join([f":pid{i}" for i in range(len(ids))])
    params = {f"pid{i}": pid for i, pid in enumerate(ids)}
    params["season"] = season
    params["ppr"] = ppr_value

    rows = execute_query(f"""
        WITH player_weeks AS (
            SELECT
                f.gsis_id,
                f.display_name,
                f.position,
                f.recent_team,
                f.week,
                f.opponent_team,
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
                AS DECIMAL(10,2)) AS week_pts
            FROM mart.fact_player_week f
            WHERE f.gsis_id IN ({placeholders})
              AND f.season = :season
              AND f.season_type = 'REG'
        )
        SELECT
            pw.gsis_id                                  AS player_id,
            pw.display_name                             AS player_name,
            pw.position,
            pw.recent_team                              AS team,
            COUNT(*)                                    AS games_played,
            CAST(AVG(pw.week_pts) AS DECIMAL(10,1))     AS ppg,
            CAST(STDEV(pw.week_pts) AS DECIMAL(10,1))   AS std_dev,
            CAST(MIN(pw.week_pts) AS DECIMAL(10,1))     AS floor,
            CAST(MAX(pw.week_pts) AS DECIMAL(10,1))     AS ceiling,
            SUM(CASE WHEN pw.week_pts >= 20 THEN 1 ELSE 0 END) AS boom_weeks,
            SUM(CASE WHEN pw.week_pts < 8 THEN 1 ELSE 0 END)   AS bust_weeks,
            CAST(AVG(pw.week_pts) / NULLIF(STDEV(pw.week_pts), 0)
                AS DECIMAL(10,2))                       AS consistency_score,
            -- Last 3 weeks average
            CAST((
                SELECT AVG(pw2.week_pts)
                FROM player_weeks pw2
                WHERE pw2.gsis_id = pw.gsis_id
                  AND pw2.week >= (SELECT MAX(week) - 2 FROM player_weeks WHERE gsis_id = pw.gsis_id)
            ) AS DECIMAL(10,1))                         AS recent_ppg
        FROM player_weeks pw
        GROUP BY pw.gsis_id, pw.display_name, pw.position, pw.recent_team
    """, params)

    return rows
