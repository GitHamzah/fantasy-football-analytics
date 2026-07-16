-- mart_dim_week.sql
{{ config(alias='dim_week') }}

-- Power BI week dimension. One row per season-week.
-- Uses a surrogate key (season * 100 + week) for a single-column PBI relationship.
-- Relationship: fact_player_week[week_key] → dim_week[week_key]

SELECT
    (season * 100) + week               AS week_key,
    season,
    week,
    season_type
FROM {{ ref('dim_week') }}
