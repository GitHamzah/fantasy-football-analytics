-- stg_pfr_pass.sql
-- Cleans Pro Football Reference advanced passing stats.
-- One row per player per week. Feeds fact_pfr_advstats.

SELECT
    game_id,
    pfr_game_id,
    CAST(season AS INT)                          AS season,
    CAST(week AS INT)                            AS week,
    game_type,
    team,
    opponent,
    pfr_player_name,
    pfr_player_id,

    -- Drops charged to this passer's receivers
    CAST(passing_drops AS INT)                   AS passing_drops,
    CAST(passing_drop_pct AS DECIMAL(8,2))       AS passing_drop_pct,
    CAST(receiving_drop AS INT)                  AS receiving_drop,
    CAST(receiving_drop_pct AS DECIMAL(8,2))     AS receiving_drop_pct,

    -- Throw quality
    CAST(passing_bad_throws AS INT)              AS passing_bad_throws,
    CAST(passing_bad_throw_pct AS DECIMAL(8,2))  AS passing_bad_throw_pct,

    -- Pressure faced
    CAST(times_sacked AS INT)                    AS times_sacked,
    CAST(times_blitzed AS INT)                   AS times_blitzed,
    CAST(times_hurried AS INT)                   AS times_hurried,
    CAST(times_hit AS INT)                       AS times_hit,
    CAST(times_pressured AS INT)                 AS times_pressured,
    CAST(times_pressured_pct AS DECIMAL(8,2))    AS times_pressured_pct,

    -- Pressure generated (present on this table but defensive in nature)
    CAST(def_times_blitzed AS INT)               AS def_times_blitzed,
    CAST(def_times_hurried AS INT)               AS def_times_hurried,
    CAST(def_times_hitqb AS INT)                 AS def_times_hitqb

FROM {{ source('raw', 'pfr_pass') }}
WHERE pfr_player_id IS NOT NULL
