-- stg_rosters_weekly.sql
-- Cleans and standardizes weekly roster snapshots.
-- One row per player per team per week.

SELECT
    gsis_id,
    CAST(season AS INT)             AS season,
    CAST(week AS INT)               AS week,
    team,
    position,
    depth_chart_position,
    jersey_number,
    status,
    full_name,
    entry_year,
    rookie_year
FROM {{ source('raw', 'rosters_weekly') }}
WHERE gsis_id IS NOT NULL
