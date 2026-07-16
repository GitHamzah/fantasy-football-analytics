-- mart_dim_game.sql
{{ config(alias='dim_game') }}

-- Power BI game dimension. One row per game.
-- Relationship: fact_player_week[game_id] → dim_game[game_id]

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
FROM {{ ref('dim_game') }}
