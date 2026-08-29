-- stg_participation.sql
-- Cleans play-level participation data and parses offense_personnel into a
-- standard grouping code. One row per play with formation data.
--
-- The feed changed shape between 2022 and 2023, so personnel is parsed two ways:
--   2021-2022: skill players only ("1 RB, 1 TE, 3 WR") — counts extracted directly.
--   2023+    : full 11-man list ("1 C, 2 G, 1 QB, 1 RB, 2 T, 1 TE, 3 WR"), with
--              ~14% of rows contaminated by defensive personnel. A row is only
--              parsed when it has exactly 1 QB and 4-6 offensive linemen;
--              otherwise personnel_grouping is NULL.
--
-- personnel_grouping = RB count digit + TE count digit ("11" = 1 RB / 1 TE,
-- "12" = 1 RB / 2 TE, ...). WR is implied.
--
-- Parsing trick: a trailing comma is appended so every position token can be
-- matched as '<digit> <POS>,' — this is what keeps '2 T,' from matching the
-- 'T' inside '1 DT,' or '1 TE,'. Counts are single digits (11 players max).

WITH src AS (

    SELECT
        nflverse_game_id,
        CAST(play_id AS INT)                        AS play_id,
        -- Season is not a raw column; the nflverse game id leads with it
        -- ("2025_01_KC_LAC").
        CAST(LEFT(nflverse_game_id, 4) AS INT)      AS season,
        possession_team,
        offense_formation,
        offense_personnel,
        defense_personnel,
        TRY_CAST(defenders_in_box AS FLOAT)         AS defenders_in_box,
        -- Comma-terminated copy that all the PATINDEX parsing runs against.
        offense_personnel + ','                     AS op
    FROM {{ source('raw', 'participation') }}
    WHERE offense_formation IS NOT NULL

),

counted AS (

    SELECT
        *,
        CASE WHEN PATINDEX('%[0-9] RB,%', op) > 0
             THEN CAST(SUBSTRING(op, PATINDEX('%[0-9] RB,%', op), 1) AS INT)
             ELSE 0 END                             AS rb_count,
        CASE WHEN PATINDEX('%[0-9] TE,%', op) > 0
             THEN CAST(SUBSTRING(op, PATINDEX('%[0-9] TE,%', op), 1) AS INT)
             ELSE 0 END                             AS te_count,
        CASE WHEN PATINDEX('%[0-9] WR,%', op) > 0
             THEN CAST(SUBSTRING(op, PATINDEX('%[0-9] WR,%', op), 1) AS INT)
             ELSE 0 END                             AS wr_count,
        CASE WHEN PATINDEX('%[0-9] QB,%', op) > 0
             THEN CAST(SUBSTRING(op, PATINDEX('%[0-9] QB,%', op), 1) AS INT)
             ELSE 0 END                             AS qb_count,
        -- Offensive line: C + G + T. '[0-9] C,' cannot match CB and
        -- '[0-9] T,' cannot match TE/DT/NT because of the terminator comma.
        CASE WHEN PATINDEX('%[0-9] C,%', op) > 0
             THEN CAST(SUBSTRING(op, PATINDEX('%[0-9] C,%', op), 1) AS INT)
             ELSE 0 END
      + CASE WHEN PATINDEX('%[0-9] G,%', op) > 0
             THEN CAST(SUBSTRING(op, PATINDEX('%[0-9] G,%', op), 1) AS INT)
             ELSE 0 END
      + CASE WHEN PATINDEX('%[0-9] T,%', op) > 0
             THEN CAST(SUBSTRING(op, PATINDEX('%[0-9] T,%', op), 1) AS INT)
             ELSE 0 END                             AS ol_count
    FROM src

)

SELECT
    nflverse_game_id,
    play_id,
    season,
    possession_team,
    offense_formation,
    offense_personnel,
    defense_personnel,
    defenders_in_box,
    CASE
        WHEN offense_personnel IS NULL THEN NULL
        -- 2021-2022: skill-only strings, trust the counts as given.
        WHEN season <= 2022
            THEN CAST(rb_count AS VARCHAR(1)) + CAST(te_count AS VARCHAR(1))
        -- 2023+: only rows that look like a real offense get a grouping.
        WHEN qb_count = 1 AND ol_count BETWEEN 4 AND 6
            THEN CAST(rb_count AS VARCHAR(1)) + CAST(te_count AS VARCHAR(1))
        ELSE NULL
    END AS personnel_grouping
FROM counted
