-- mart_dim_team.sql
{{ config(alias='dim_team') }}

-- Power BI team dimension. One row per team.
-- Relationship: fact_player_week[recent_team] → dim_team[team_abbr]

SELECT
    team_abbr
FROM {{ ref('dim_team') }}
