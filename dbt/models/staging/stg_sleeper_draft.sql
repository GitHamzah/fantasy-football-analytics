-- stg_sleeper_draft.sql
-- One row per draft pick, bridged to nflverse ids. (The pick's Sleeper player
-- id lives in draft_pick.player_id, aliased here to player_sleeper_id.)

SELECT
    dp.league_id,
    dp.draft_id,
    dp.round,
    dp.pick_no,
    dp.player_id        AS player_sleeper_id,
    pm.gsis_id,
    pm.full_name        AS player_name,
    pm.position,
    pm.team,
    dp.picked_by        AS drafter_user_id,
    dp.roster_id,
    dp.season,
    l.name              AS league_name
FROM {{ source('sleeper', 'draft_pick') }} dp
LEFT JOIN {{ source('sleeper', 'player_map') }} pm
    ON dp.player_id = pm.sleeper_id
LEFT JOIN {{ source('sleeper', 'league') }} l
    ON dp.league_id = l.league_id
