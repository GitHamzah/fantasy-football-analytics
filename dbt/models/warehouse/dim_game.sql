-- dim_game.sql
-- One row per NFL game with teams, scores, and venue metadata.
-- Materialized as a table in the warehouse schema.

SELECT
    game_id,
    season,
    week,
    game_type,
    gameday,
    gametime,
    home_team,
    away_team,
    home_score,
    away_score,
    spread_line,
    total_line,
    stadium,
    roof,
    surface
FROM {{ ref('stg_schedules') }}
