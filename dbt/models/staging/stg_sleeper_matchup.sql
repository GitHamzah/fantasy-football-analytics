-- stg_sleeper_matchup.sql
-- One row per roster per week per league, with points scored.

SELECT
    m.league_id,
    m.week,
    m.roster_id,
    m.matchup_id,
    CAST(m.points AS FLOAT) AS points,
    m.season,
    l.name                  AS league_name
FROM {{ source('sleeper', 'matchup') }} m
LEFT JOIN {{ source('sleeper', 'league') }} l
    ON m.league_id = l.league_id
