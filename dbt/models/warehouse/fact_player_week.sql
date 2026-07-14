-- fact_player_week.sql
-- Core fact table: one row per player per week with all stat components.
-- Fantasy points are NOT calculated here — they belong in the mart layer.
-- Materialized as a table in the warehouse schema.

SELECT
    s.gsis_id,
    s.display_name,
    s.season,
    s.week,
    s.season_type,
    s.game_id,
    s.recent_team,
    s.opponent_team,
    s.position,
    s.position_group,

    -- Passing
    s.completions,
    s.attempts,
    s.passing_yards,
    s.passing_tds,
    s.interceptions,
    s.sacks,
    s.sack_yards,
    s.sack_fumbles_lost,
    s.passing_air_yards,
    s.passing_yac,
    s.passing_first_downs,
    s.passing_epa,
    s.passing_2pt_conversions,

    -- Rushing
    s.carries,
    s.rushing_yards,
    s.rushing_tds,
    s.rushing_fumbles_lost,
    s.rushing_first_downs,
    s.rushing_epa,
    s.rushing_2pt_conversions,

    -- Receiving
    s.receptions,
    s.targets,
    s.receiving_yards,
    s.receiving_tds,
    s.receiving_fumbles_lost,
    s.receiving_air_yards,
    s.receiving_yac,
    s.receiving_first_downs,
    s.receiving_epa,
    s.receiving_2pt_conversions,

    -- Usage / share
    s.target_share,
    s.air_yards_share,
    s.wopr,

    -- Special teams
    s.special_teams_tds,

    -- Source fantasy points (validation only)
    s.source_fantasy_points,
    s.source_fantasy_points_ppr

FROM {{ ref('stg_player_stats') }} s
