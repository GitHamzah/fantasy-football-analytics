-- mart_dim_player.sql
{{ config(alias='dim_player') }}

-- Power BI player dimension. One row per player.
-- Relationship: fact_player_week[gsis_id] → dim_player[gsis_id]

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
FROM {{ ref('dim_player') }}
