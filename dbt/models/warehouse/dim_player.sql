-- dim_player.sql
-- One row per player. Materialized as a table in the warehouse schema.
-- Source: stg_players

SELECT
    gsis_id,
    display_name,
    first_name,
    last_name,
    position,
    position_group,
    height_inches,
    weight_lbs,
    birth_date,
    college,
    rookie_year,
    draft_year,
    draft_round,
    draft_pick,
    status,
    current_team
FROM {{ ref('stg_players') }}