{{ config(alias='league_matchup', materialized='table') }}

-- Weekly head-to-head scores for every league, with the manager name resolved
-- through roster ownership. Backs /leagues/{id}/matchups on Neon, where the
-- sleeper schema is not synced.

SELECT
    m.league_id,
    m.league_name,
    m.season,
    m.week,
    m.matchup_id,
    m.roster_id,
    m.points,
    u.display_name  AS manager_name,
    r.owner_id      AS user_id
FROM {{ ref('stg_sleeper_matchup') }} m
LEFT JOIN {{ source('sleeper', 'roster') }} r
    ON r.league_id = m.league_id AND r.roster_id = m.roster_id
LEFT JOIN {{ source('sleeper', 'user') }} u
    ON u.user_id = r.owner_id AND u.league_id = m.league_id
