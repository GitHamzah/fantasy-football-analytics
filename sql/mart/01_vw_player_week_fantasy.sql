-- ============================================
-- mart.vw_player_week_fantasy
-- Calculates fantasy points per player-week for every scoring format.
-- This is the primary Power BI source for fantasy analysis.
-- Fantasy points are computed here, not stored in the fact table.
-- ============================================

CREATE OR ALTER VIEW mart.vw_player_week_fantasy
AS
SELECT
    fpw.fact_player_week_key,

    -- Player
    fpw.gsis_id,
    dp.display_name,
    dp.position,
    dp.position_group,

    -- Time
    fpw.season,
    fpw.week,
    dw.season_type,

    -- Team / Game
    fpw.recent_team,
    fpw.opponent_team,
    dg.gameday,
    dg.home_team,
    dg.away_team,

    -- Scoring format
    sf.format_name          AS scoring_format,

    -- Raw stat components (for detail drilldowns)
    fpw.completions,
    fpw.attempts,
    fpw.passing_yards,
    fpw.passing_tds,
    fpw.interceptions,
    fpw.carries,
    fpw.rushing_yards,
    fpw.rushing_tds,
    fpw.receptions,
    fpw.targets,
    fpw.receiving_yards,
    fpw.receiving_tds,
    fpw.target_share,
    fpw.air_yards_share,
    fpw.wopr,
    fpw.special_teams_tds,

    -- Fumbles (combined)
    ISNULL(fpw.sack_fumbles_lost, 0)
        + ISNULL(fpw.rushing_fumbles_lost, 0)
        + ISNULL(fpw.receiving_fumbles_lost, 0)
        AS total_fumbles_lost,

    -- 2pt conversions (combined)
    ISNULL(fpw.passing_2pt_conversions, 0)
        + ISNULL(fpw.rushing_2pt_conversions, 0)
        + ISNULL(fpw.receiving_2pt_conversions, 0)
        AS total_2pt_conversions,

    -- Calculated fantasy points
    CAST(
        ISNULL(fpw.passing_yards, 0)   * sf.pts_passing_yard
      + ISNULL(fpw.passing_tds, 0)     * sf.pts_passing_td
      + ISNULL(fpw.interceptions, 0)   * sf.pts_interception
      + ISNULL(fpw.rushing_yards, 0)   * sf.pts_rushing_yard
      + ISNULL(fpw.rushing_tds, 0)     * sf.pts_rushing_td
      + ISNULL(fpw.receptions, 0)      * sf.pts_per_reception
      + ISNULL(fpw.receiving_yards, 0) * sf.pts_receiving_yard
      + ISNULL(fpw.receiving_tds, 0)   * sf.pts_receiving_td
      + (ISNULL(fpw.sack_fumbles_lost, 0)
         + ISNULL(fpw.rushing_fumbles_lost, 0)
         + ISNULL(fpw.receiving_fumbles_lost, 0)) * sf.pts_fumble_lost
      + (ISNULL(fpw.passing_2pt_conversions, 0)
         + ISNULL(fpw.rushing_2pt_conversions, 0)
         + ISNULL(fpw.receiving_2pt_conversions, 0)) * sf.pts_2pt_conversion
      + ISNULL(fpw.special_teams_tds, 0) * sf.pts_rushing_td  -- scored as rushing TD points
    AS DECIMAL(10,2))
        AS fantasy_points,

    -- Source fantasy points for validation
    fpw.source_fantasy_points,
    fpw.source_fantasy_points_ppr

FROM warehouse.fact_player_week fpw
INNER JOIN warehouse.dim_player dp
    ON fpw.player_key = dp.player_key
INNER JOIN warehouse.dim_week dw
    ON fpw.week_key = dw.week_key
LEFT JOIN warehouse.dim_game dg
    ON fpw.game_key = dg.game_key
CROSS JOIN warehouse.dim_scoring_format sf;
GO
