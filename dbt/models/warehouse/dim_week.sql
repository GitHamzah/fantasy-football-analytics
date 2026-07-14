-- dim_week.sql
-- One row per season-week combination.
-- Materialized as a table in the warehouse schema.

SELECT DISTINCT
    season,
    week,
    game_type  AS season_type
FROM {{ ref('stg_schedules') }}
