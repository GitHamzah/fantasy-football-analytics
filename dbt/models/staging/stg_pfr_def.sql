-- stg_pfr_def.sql
-- Cleans Pro Football Reference advanced defensive stats.
-- One row per player per week. Feeds fact_pfr_advstats.

SELECT
    game_id,
    pfr_game_id,
    CAST(season AS INT)                                 AS season,
    CAST(week AS INT)                                   AS week,
    game_type,
    team,
    opponent,
    pfr_player_name,
    pfr_player_id,

    -- Coverage: what happened when this defender was targeted
    CAST(def_ints AS INT)                               AS def_ints,
    CAST(def_targets AS INT)                            AS def_targets,
    CAST(def_completions_allowed AS INT)                AS def_completions_allowed,
    CAST(def_completion_pct AS DECIMAL(8,2))            AS def_completion_pct,
    CAST(def_yards_allowed AS DECIMAL(8,1))             AS def_yards_allowed,
    CAST(def_yards_allowed_per_cmp AS DECIMAL(8,2))     AS def_yards_allowed_per_cmp,
    CAST(def_yards_allowed_per_tgt AS DECIMAL(8,2))     AS def_yards_allowed_per_tgt,
    CAST(def_receiving_td_allowed AS INT)               AS def_receiving_td_allowed,
    CAST(def_passer_rating_allowed AS DECIMAL(8,2))     AS def_passer_rating_allowed,
    CAST(def_adot AS DECIMAL(8,2))                      AS def_adot,
    CAST(def_air_yards_completed AS DECIMAL(8,1))       AS def_air_yards_completed,
    CAST(def_yards_after_catch AS DECIMAL(8,1))         AS def_yards_after_catch,

    -- Pass rush. Sacks are recorded in half increments, so keep a decimal.
    CAST(def_times_blitzed AS INT)                      AS def_times_blitzed,
    CAST(def_times_hurried AS INT)                      AS def_times_hurried,
    CAST(def_times_hitqb AS INT)                        AS def_times_hitqb,
    CAST(def_sacks AS DECIMAL(8,1))                     AS def_sacks,
    CAST(def_pressures AS INT)                          AS def_pressures,

    -- Tackling
    CAST(def_tackles_combined AS INT)                   AS def_tackles_combined,
    CAST(def_missed_tackles AS INT)                     AS def_missed_tackles,
    CAST(def_missed_tackle_pct AS DECIMAL(8,2))         AS def_missed_tackle_pct

FROM {{ source('raw', 'pfr_def') }}
WHERE pfr_player_id IS NOT NULL
