-- stg_schedules.sql
-- Cleans and standardizes game schedule data.
-- One row per game. Feeds dim_game and dim_week in the warehouse layer.

SELECT
    game_id,
    CAST(season AS INT)                     AS season,
    CAST(week AS INT)                       AS week,
    game_type,
    CAST(gameday AS DATE)                   AS gameday,
    gametime,
    home_team,
    away_team,
    CAST(home_score AS INT)                 AS home_score,
    CAST(away_score AS INT)                 AS away_score,
    CAST(spread_line AS DECIMAL(5,1))       AS spread_line,
    CAST(total_line AS DECIMAL(5,1))        AS total_line,
    stadium,
    roof,
    surface
FROM {{ source('raw', 'schedules') }}
WHERE game_id IS NOT NULL
