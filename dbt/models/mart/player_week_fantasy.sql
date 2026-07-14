-- player_week_fantasy.sql
-- Power BI primary source. Calculates fantasy points per player-week
-- for every scoring format via cross join with scoring_formats seed.
-- Materialized as a view in the mart schema.

WITH fact AS (
    SELECT * FROM {{ ref('fact_player_week') }}
),

scoring AS (
    SELECT * FROM {{ ref('scoring_formats') }}
),

games AS (
    SELECT
        game_id,
        gameday
    FROM {{ ref('dim_game') }}
)

SELECT
    -- Player
    f.gsis_id,
    f.display_name,
    f.position,
    f.position_group,

    -- Time
    f.season,
    f.week,
    f.season_type,

    -- Team / Game
    f.recent_team,
    f.opponent_team,
    g.gameday,

    -- Scoring format
    sf.format_name                          AS scoring_format,

    -- Raw stat components
    f.completions,
    f.attempts,
    f.passing_yards,
    f.passing_tds,
    f.interceptions,
    f.carries,
    f.rushing_yards,
    f.rushing_tds,
    f.receptions,
    f.targets,
    f.receiving_yards,
    f.receiving_tds,
    f.target_share,
    f.air_yards_share,
    f.wopr,
    f.special_teams_tds,

    -- Combined fumbles
    ISNULL(f.sack_fumbles_lost, 0)
        + ISNULL(f.rushing_fumbles_lost, 0)
        + ISNULL(f.receiving_fumbles_lost, 0)
                                            AS total_fumbles_lost,

    -- Combined 2pt conversions
    ISNULL(f.passing_2pt_conversions, 0)
        + ISNULL(f.rushing_2pt_conversions, 0)
        + ISNULL(f.receiving_2pt_conversions, 0)
                                            AS total_2pt_conversions,

    -- Calculated fantasy points
    CAST(
        ISNULL(f.passing_yards, 0)   * sf.pts_passing_yard
      + ISNULL(f.passing_tds, 0)     * sf.pts_passing_td
      + ISNULL(f.interceptions, 0)   * sf.pts_interception
      + ISNULL(f.rushing_yards, 0)   * sf.pts_rushing_yard
      + ISNULL(f.rushing_tds, 0)     * sf.pts_rushing_td
      + ISNULL(f.receptions, 0)      * sf.pts_per_reception
      + ISNULL(f.receiving_yards, 0) * sf.pts_receiving_yard
      + ISNULL(f.receiving_tds, 0)   * sf.pts_receiving_td
      + (ISNULL(f.sack_fumbles_lost, 0)
         + ISNULL(f.rushing_fumbles_lost, 0)
         + ISNULL(f.receiving_fumbles_lost, 0)) * sf.pts_fumble_lost
      + (ISNULL(f.passing_2pt_conversions, 0)
         + ISNULL(f.rushing_2pt_conversions, 0)
         + ISNULL(f.receiving_2pt_conversions, 0)) * sf.pts_2pt_conversion
      + ISNULL(f.special_teams_tds, 0) * sf.pts_rushing_td
    AS DECIMAL(10,2))                       AS fantasy_points,

    -- Source values for validation
    f.source_fantasy_points,
    f.source_fantasy_points_ppr

FROM fact f
CROSS JOIN scoring sf
LEFT JOIN games g
    ON f.game_id = g.game_id
