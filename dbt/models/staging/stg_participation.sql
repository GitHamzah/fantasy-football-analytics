-- stg_participation.sql
-- Cleans play-level participation data and parses BOTH personnel strings:
-- offense_personnel into a standard grouping code, defense_personnel into
-- DL/LB/DB counts, a package label, and a coverage-shell approximation.
-- One row per play with formation data.
--
-- The feed changed shape between 2022 and 2023, so parsing is era-aware:
--   2021-2022 offense: skill players only ("1 RB, 1 TE, 3 WR").
--   2021-2022 defense: pre-aggregated groups ("4 DL, 2 LB, 5 DB").
--   2023+    : full 11-man position lists for both sides, with ~14% of rows
--              cross-contaminated. Offense rows are validated by QB/OL counts;
--              defense rows by total defenders in 10-11 (tracking noise allows
--              a man short). Failing rows get NULL groupings.
--
-- offense personnel_grouping = RB digit + TE digit ("11" = 1 RB / 1 TE).
-- def_personnel_grouping     = named package (Nickel, 4-3 Base, ...) or
--                              "{DL}-{LB}-{DB}" when unnamed.
--
-- Parsing trick: a trailing comma is appended so every position token can be
-- matched as '<digit> <POS>,' — this is what keeps '2 T,' from matching the
-- 'T' inside '1 DT,' or '1 TE,', and '1 S,' from matching 'FS,'/'SS,'/'LS,'.
-- Counts are single digits (11 players max). The defensive group sums work
-- for both eras with no branch: legacy strings carry DL/LB/DB tokens, new
-- strings carry the specific positions, and the tokens never coexist.

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
        -- Comma-terminated copies that all the PATINDEX parsing runs against.
        offense_personnel + ','                     AS op,
        defense_personnel + ','                     AS dp
    FROM {{ source('raw', 'participation') }}
    WHERE offense_formation IS NOT NULL

),

counted AS (

    SELECT
        *,
        -- ---- offense ----
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
             ELSE 0 END                             AS ol_count,

        -- ---- defense: line (DL token is legacy, DE/DT/NT are 2023+) ----
        CASE WHEN PATINDEX('%[0-9] DL,%', dp) > 0
             THEN CAST(SUBSTRING(dp, PATINDEX('%[0-9] DL,%', dp), 1) AS INT)
             ELSE 0 END
      + CASE WHEN PATINDEX('%[0-9] DE,%', dp) > 0
             THEN CAST(SUBSTRING(dp, PATINDEX('%[0-9] DE,%', dp), 1) AS INT)
             ELSE 0 END
      + CASE WHEN PATINDEX('%[0-9] DT,%', dp) > 0
             THEN CAST(SUBSTRING(dp, PATINDEX('%[0-9] DT,%', dp), 1) AS INT)
             ELSE 0 END
      + CASE WHEN PATINDEX('%[0-9] NT,%', dp) > 0
             THEN CAST(SUBSTRING(dp, PATINDEX('%[0-9] NT,%', dp), 1) AS INT)
             ELSE 0 END                             AS def_dl_count,

        -- ---- defense: linebackers ('[0-9] LB,' cannot match MLB/ILB/OLB) ----
        CASE WHEN PATINDEX('%[0-9] LB,%', dp) > 0
             THEN CAST(SUBSTRING(dp, PATINDEX('%[0-9] LB,%', dp), 1) AS INT)
             ELSE 0 END
      + CASE WHEN PATINDEX('%[0-9] MLB,%', dp) > 0
             THEN CAST(SUBSTRING(dp, PATINDEX('%[0-9] MLB,%', dp), 1) AS INT)
             ELSE 0 END
      + CASE WHEN PATINDEX('%[0-9] ILB,%', dp) > 0
             THEN CAST(SUBSTRING(dp, PATINDEX('%[0-9] ILB,%', dp), 1) AS INT)
             ELSE 0 END
      + CASE WHEN PATINDEX('%[0-9] OLB,%', dp) > 0
             THEN CAST(SUBSTRING(dp, PATINDEX('%[0-9] OLB,%', dp), 1) AS INT)
             ELSE 0 END
      + CASE WHEN PATINDEX('%[0-9] SLB,%', dp) > 0
             THEN CAST(SUBSTRING(dp, PATINDEX('%[0-9] SLB,%', dp), 1) AS INT)
             ELSE 0 END
      + CASE WHEN PATINDEX('%[0-9] WLB,%', dp) > 0
             THEN CAST(SUBSTRING(dp, PATINDEX('%[0-9] WLB,%', dp), 1) AS INT)
             ELSE 0 END                             AS def_lb_count,

        -- ---- defense: secondary ('[0-9] S,' cannot match FS/SS/LS) ----
        CASE WHEN PATINDEX('%[0-9] DB,%', dp) > 0
             THEN CAST(SUBSTRING(dp, PATINDEX('%[0-9] DB,%', dp), 1) AS INT)
             ELSE 0 END
      + CASE WHEN PATINDEX('%[0-9] CB,%', dp) > 0
             THEN CAST(SUBSTRING(dp, PATINDEX('%[0-9] CB,%', dp), 1) AS INT)
             ELSE 0 END
      + CASE WHEN PATINDEX('%[0-9] FS,%', dp) > 0
             THEN CAST(SUBSTRING(dp, PATINDEX('%[0-9] FS,%', dp), 1) AS INT)
             ELSE 0 END
      + CASE WHEN PATINDEX('%[0-9] SS,%', dp) > 0
             THEN CAST(SUBSTRING(dp, PATINDEX('%[0-9] SS,%', dp), 1) AS INT)
             ELSE 0 END
      + CASE WHEN PATINDEX('%[0-9] SAF,%', dp) > 0
             THEN CAST(SUBSTRING(dp, PATINDEX('%[0-9] SAF,%', dp), 1) AS INT)
             ELSE 0 END
      + CASE WHEN PATINDEX('%[0-9] S,%', dp) > 0
             THEN CAST(SUBSTRING(dp, PATINDEX('%[0-9] S,%', dp), 1) AS INT)
             ELSE 0 END                             AS def_db_count
    FROM src

),

labeled AS (

    SELECT
        *,
        -- A 2023+ defense string is trusted only when it accounts for a full
        -- unit (10-11 defenders; one short happens in tracking). Legacy
        -- strings are pre-aggregated and taken as given.
        CASE
            WHEN defense_personnel IS NULL THEN 0
            WHEN season <= 2022 THEN 1
            WHEN def_dl_count + def_lb_count + def_db_count BETWEEN 10 AND 11 THEN 1
            ELSE 0
        END AS def_counts_valid
    FROM counted

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
    END AS personnel_grouping,

    CASE WHEN def_counts_valid = 1 THEN def_dl_count END AS def_dl_count,
    CASE WHEN def_counts_valid = 1 THEN def_lb_count END AS def_lb_count,
    CASE WHEN def_counts_valid = 1 THEN def_db_count END AS def_db_count,

    CASE
        WHEN def_counts_valid = 0 THEN NULL
        WHEN def_dl_count = 4 AND def_lb_count = 3 AND def_db_count = 4 THEN '4-3 Base'
        WHEN def_dl_count = 3 AND def_lb_count = 4 AND def_db_count = 4 THEN '3-4 Base'
        WHEN def_db_count = 5 THEN 'Nickel'
        WHEN def_db_count = 6 THEN 'Dime'
        WHEN def_db_count >= 7 THEN 'Quarter'
        WHEN def_dl_count >= 5 AND def_db_count <= 3 THEN 'Goal Line'
        ELSE CAST(def_dl_count AS VARCHAR(2)) + '-'
           + CAST(def_lb_count AS VARCHAR(2)) + '-'
           + CAST(def_db_count AS VARCHAR(2))
    END AS def_personnel_grouping,

    -- Box-count proxy for the coverage shell. Range checks rather than
    -- equality because the column is FLOAT.
    CASE
        WHEN defenders_in_box IS NULL THEN NULL
        WHEN defenders_in_box < 7 THEN '2-High'
        WHEN defenders_in_box < 8 THEN '1-High'
        ELSE 'Loaded Box'
    END AS coverage_shell
FROM labeled
