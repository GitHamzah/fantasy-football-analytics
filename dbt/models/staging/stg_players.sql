-- stg_players.sql
-- Cleans and standardizes the raw player universe.
-- One row per player. This feeds dim_player in the warehouse layer.

SELECT
    gsis_id,
    display_name,
    first_name,
    last_name,
    position,
    position_group,
    CAST(height AS INT)                     AS height_inches,
    CAST(weight AS INT)                     AS weight_lbs,
    CAST(birth_date AS DATE)                AS birth_date,
    college_name                            AS college,
    CAST(rookie_season AS INT)              AS rookie_year,
    CAST(draft_year AS INT)                 AS draft_year,
    CAST(draft_round AS INT)                AS draft_round,
    CAST(draft_pick AS INT)                 AS draft_pick,
    status,
    latest_team                             AS current_team
FROM {{ source('raw', 'players') }}
WHERE gsis_id IS NOT NULL
