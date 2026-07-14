-- dim_team.sql
-- One row per team. Derived from schedule data.
-- Materialized as a table in the warehouse schema.

WITH home_teams AS (
    SELECT DISTINCT home_team AS team_abbr
    FROM {{ ref('stg_schedules') }}
),

away_teams AS (
    SELECT DISTINCT away_team AS team_abbr
    FROM {{ ref('stg_schedules') }}
),

all_teams AS (
    SELECT team_abbr FROM home_teams
    UNION
    SELECT team_abbr FROM away_teams
)

SELECT
    team_abbr
FROM all_teams
WHERE team_abbr IS NOT NULL
