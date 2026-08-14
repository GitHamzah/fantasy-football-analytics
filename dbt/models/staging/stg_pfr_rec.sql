-- stg_pfr_rec.sql
-- Cleans Pro Football Reference advanced receiving stats.
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

    CAST(rushing_broken_tackles AS INT)          AS rushing_broken_tackles,
    CAST(receiving_broken_tackles AS INT)        AS receiving_broken_tackles,

    -- Drops
    CAST(passing_drops AS INT)                   AS passing_drops,
    CAST(passing_drop_pct AS DECIMAL(8,2))       AS passing_drop_pct,
    CAST(receiving_drop AS INT)                  AS receiving_drop,
    CAST(receiving_drop_pct AS DECIMAL(8,2))     AS receiving_drop_pct,

    -- Quality of targets drawn
    CAST(receiving_int AS INT)                   AS receiving_int,
    CAST(receiving_rat AS DECIMAL(8,2))          AS receiving_rat

FROM {{ source('raw', 'pfr_rec') }}
WHERE pfr_player_id IS NOT NULL
