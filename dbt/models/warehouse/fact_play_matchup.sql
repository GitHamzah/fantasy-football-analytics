-- fact_play_matchup.sql
-- Every pass/run snap with its formation and personnel context: pbp outcomes
-- joined to participation on nflverse_game_id + play_id. One row per play,
-- ~170K rows across five seasons.
--
-- LEFT JOIN by design: pbp is the spine, and plays with no participation row
-- (or with unparsed personnel) keep NULL context rather than disappearing —
-- aggregations over formation dimensions simply won't see them.
--
-- Too large for the Neon sync; only the mart-level aggregations ship.
-- Materialized as a table in the warehouse schema.

SELECT
    pbp.nflverse_game_id,
    pbp.play_id,
    pbp.posteam,
    pbp.defteam,
    pbp.season,
    pbp.week,
    pbp.play_type,
    pbp.yards_gained,
    pbp.passing_yards,
    pbp.rushing_yards,
    pbp.receiving_yards,
    pbp.touchdown,
    pbp.interception,
    pbp.fumble_lost,
    pbp.epa,
    pbp.success,
    pbp.down,
    pbp.ydstogo,
    pbp.complete_pass,
    pbp.receiver_player_id,
    pbp.receiver_player_name,
    pbp.rusher_player_id,
    pbp.rusher_player_name,
    pbp.passer_player_id,
    pbp.passer_player_name,

    -- Context from participation
    part.offense_formation,
    part.personnel_grouping                     AS off_personnel,
    part.def_personnel_grouping                 AS def_package,
    part.coverage_shell
FROM {{ ref('stg_pbp') }} pbp
LEFT JOIN {{ ref('stg_participation') }} part
    ON pbp.nflverse_game_id = part.nflverse_game_id
   AND pbp.play_id = part.play_id
