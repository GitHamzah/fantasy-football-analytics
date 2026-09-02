-- stg_sleeper_roster.sql
-- One row per rostered player per league, with the nflverse bridge (gsis_id),
-- league context and the manager's display name attached.

SELECT
    rp.league_id,
    rp.roster_id,
    rp.owner_id,
    rp.sleeper_id,
    rp.is_starter,
    rp.season,
    pm.gsis_id,
    pm.full_name        AS player_name,
    pm.position,
    pm.team,
    l.name              AS league_name,
    l.status            AS league_status,
    l.total_rosters,
    u.display_name      AS manager_name
FROM {{ source('sleeper', 'roster_player') }} rp
LEFT JOIN {{ source('sleeper', 'player_map') }} pm
    ON rp.sleeper_id = pm.sleeper_id
LEFT JOIN {{ source('sleeper', 'league') }} l
    ON rp.league_id = l.league_id
LEFT JOIN {{ source('sleeper', 'user') }} u
    ON rp.owner_id = u.user_id AND rp.league_id = u.league_id
