-- stg_pfr_rush.sql
-- Cleans Pro Football Reference advanced rushing stats.
-- One row per player per week. Feeds fact_pfr_advstats.

SELECT
    game_id,
    pfr_game_id,
    CAST(season AS INT)                                     AS season,
    CAST(week AS INT)                                       AS week,
    game_type,
    team,
    opponent,
    pfr_player_name,
    pfr_player_id,

    CAST(carries AS INT)                                    AS carries,

    -- Contact-adjusted rushing production
    CAST(rushing_yards_before_contact AS DECIMAL(8,1))      AS rushing_yards_before_contact,
    CAST(rushing_yards_before_contact_avg AS DECIMAL(8,2))  AS rushing_yards_before_contact_avg,
    CAST(rushing_yards_after_contact AS DECIMAL(8,1))       AS rushing_yards_after_contact,
    CAST(rushing_yards_after_contact_avg AS DECIMAL(8,2))   AS rushing_yards_after_contact_avg,

    CAST(rushing_broken_tackles AS INT)                     AS rushing_broken_tackles,
    CAST(receiving_broken_tackles AS INT)                   AS receiving_broken_tackles

FROM {{ source('raw', 'pfr_rush') }}
WHERE pfr_player_id IS NOT NULL
