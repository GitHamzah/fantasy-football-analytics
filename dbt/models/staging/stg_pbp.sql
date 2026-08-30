-- stg_pbp.sql
-- Cleans play-by-play pass/run snaps. One row per offensive play.
-- Joins to stg_participation on nflverse_game_id + play_id; that is the whole
-- reason this feed exists here — pbp has outcomes (yards, EPA, players),
-- participation has context (formation, personnel, coverage shell).

SELECT
    nflverse_game_id,
    CAST(play_id AS INT)                        AS play_id,
    posteam,
    defteam,
    CAST(season AS INT)                         AS season,
    CAST(week AS INT)                           AS week,
    play_type,
    CAST(yards_gained AS FLOAT)                 AS yards_gained,
    CAST(passing_yards AS FLOAT)                AS passing_yards,
    CAST(rushing_yards AS FLOAT)                AS rushing_yards,
    CAST(receiving_yards AS FLOAT)              AS receiving_yards,
    CAST(touchdown AS INT)                      AS touchdown,
    CAST(interception AS INT)                   AS interception,
    CAST(fumble_lost AS INT)                    AS fumble_lost,
    CAST(epa AS FLOAT)                          AS epa,
    CAST(success AS INT)                        AS success,
    CAST(down AS INT)                           AS down,
    CAST(ydstogo AS INT)                        AS ydstogo,
    CAST(score_differential AS FLOAT)           AS score_differential,
    CAST(wp AS FLOAT)                           AS wp,
    CAST(complete_pass AS INT)                  AS complete_pass,
    receiver_player_id,
    receiver_player_name,
    rusher_player_id,
    rusher_player_name,
    passer_player_id,
    passer_player_name
FROM {{ source('raw', 'pbp') }}
-- Raw is already filtered at ingest; restated here so the model stands on its
-- own if the raw filter ever loosens.
WHERE play_type IN ('pass', 'run')
  AND nflverse_game_id IS NOT NULL
