-- stg_player_stats.sql
-- Cleans and standardizes weekly player stat lines.
-- One row per player per week. Feeds fact_player_week in the warehouse layer.

SELECT
    player_id                                        AS gsis_id,
    player_display_name                              AS display_name,
    CAST(season AS INT)                              AS season,
    CAST(week AS INT)                                AS week,
    season_type,
    game_id,
    team                                             AS recent_team,
    opponent_team,
    position,
    position_group,

    -- Passing
    CAST(ISNULL(completions, 0) AS INT)              AS completions,
    CAST(ISNULL(attempts, 0) AS INT)                 AS attempts,
    CAST(ISNULL(passing_yards, 0) AS DECIMAL(8,1))   AS passing_yards,
    CAST(ISNULL(passing_tds, 0) AS INT)              AS passing_tds,
    CAST(ISNULL(passing_interceptions, 0) AS INT)    AS interceptions,
    CAST(ISNULL(sacks_suffered, 0) AS INT)           AS sacks,
    CAST(ISNULL(sack_yards_lost, 0) AS DECIMAL(8,1)) AS sack_yards,
    CAST(ISNULL(sack_fumbles_lost, 0) AS INT)        AS sack_fumbles_lost,
    CAST(passing_air_yards AS DECIMAL(8,1))           AS passing_air_yards,
    CAST(passing_yards_after_catch AS DECIMAL(8,1))   AS passing_yac,
    CAST(ISNULL(passing_first_downs, 0) AS INT)      AS passing_first_downs,
    CAST(passing_epa AS DECIMAL(10,3))                AS passing_epa,
    CAST(ISNULL(passing_2pt_conversions, 0) AS INT)  AS passing_2pt_conversions,

    -- Rushing
    CAST(ISNULL(carries, 0) AS INT)                  AS carries,
    CAST(ISNULL(rushing_yards, 0) AS DECIMAL(8,1))   AS rushing_yards,
    CAST(ISNULL(rushing_tds, 0) AS INT)              AS rushing_tds,
    CAST(ISNULL(rushing_fumbles_lost, 0) AS INT)     AS rushing_fumbles_lost,
    CAST(ISNULL(rushing_first_downs, 0) AS INT)      AS rushing_first_downs,
    CAST(rushing_epa AS DECIMAL(10,3))                AS rushing_epa,
    CAST(ISNULL(rushing_2pt_conversions, 0) AS INT)  AS rushing_2pt_conversions,

    -- Receiving
    CAST(ISNULL(receptions, 0) AS INT)               AS receptions,
    CAST(ISNULL(targets, 0) AS INT)                  AS targets,
    CAST(ISNULL(receiving_yards, 0) AS DECIMAL(8,1)) AS receiving_yards,
    CAST(ISNULL(receiving_tds, 0) AS INT)            AS receiving_tds,
    CAST(ISNULL(receiving_fumbles_lost, 0) AS INT)   AS receiving_fumbles_lost,
    CAST(receiving_air_yards AS DECIMAL(8,1))         AS receiving_air_yards,
    CAST(receiving_yards_after_catch AS DECIMAL(8,1)) AS receiving_yac,
    CAST(ISNULL(receiving_first_downs, 0) AS INT)    AS receiving_first_downs,
    CAST(receiving_epa AS DECIMAL(10,3))              AS receiving_epa,
    CAST(ISNULL(receiving_2pt_conversions, 0) AS INT) AS receiving_2pt_conversions,

    -- Usage / share
    CAST(target_share AS DECIMAL(6,4))                AS target_share,
    CAST(air_yards_share AS DECIMAL(6,4))             AS air_yards_share,
    CAST(wopr AS DECIMAL(6,4))                        AS wopr,

    -- Special teams
    CAST(ISNULL(special_teams_tds, 0) AS INT)        AS special_teams_tds,

    -- Source fantasy points (kept for validation only)
    CAST(fantasy_points AS DECIMAL(8,2))              AS source_fantasy_points,
    CAST(fantasy_points_ppr AS DECIMAL(8,2))          AS source_fantasy_points_ppr

FROM {{ source('raw', 'player_stats') }}
WHERE player_id IS NOT NULL
