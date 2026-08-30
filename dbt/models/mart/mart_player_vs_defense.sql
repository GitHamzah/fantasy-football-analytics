{{ config(alias='player_vs_defense', materialized='table') }}

-- Player performance split by the defense faced: one row per player-season-
-- defense-package-shell, in three roles stacked by UNION ALL.
--
-- Column semantics per role (one schema so the union lines up):
--   attempts    = targets (WR/TE) / carries (RB) / dropbacks (QB)
--   completions = receptions (WR/TE) / NULL (RB) / completions (QB)
--   yards       = receiving / rushing / passing
--   tds, interceptions, avg_epa, avg_yards mean the obvious thing per role.
--
-- Rows with NULL def_package or coverage_shell are kept — they aggregate the
-- plays whose formation context is unknown, and dropping them would silently
-- shrink a player's totals. Materialized as a table so Neon sync reads it.

SELECT
    receiver_player_id                              AS player_id,
    receiver_player_name                            AS player_name,
    'WR/TE'                                         AS role,
    defteam,
    season,
    def_package,
    coverage_shell,
    COUNT(*)                                        AS attempts,
    SUM(COALESCE(complete_pass, 0))                 AS completions,
    SUM(COALESCE(receiving_yards, 0))               AS yards,
    SUM(COALESCE(touchdown, 0))                     AS tds,
    SUM(COALESCE(interception, 0))                  AS interceptions,
    AVG(epa)                                        AS avg_epa,
    AVG(yards_gained)                               AS avg_yards
FROM {{ ref('fact_play_matchup') }}
WHERE play_type = 'pass' AND receiver_player_id IS NOT NULL
GROUP BY receiver_player_id, receiver_player_name, defteam, season,
         def_package, coverage_shell

UNION ALL

SELECT
    rusher_player_id                                AS player_id,
    rusher_player_name                              AS player_name,
    'RB'                                            AS role,
    defteam,
    season,
    def_package,
    coverage_shell,
    COUNT(*)                                        AS attempts,
    NULL                                            AS completions,
    SUM(COALESCE(rushing_yards, 0))                 AS yards,
    SUM(COALESCE(touchdown, 0))                     AS tds,
    NULL                                            AS interceptions,
    AVG(epa)                                        AS avg_epa,
    AVG(yards_gained)                               AS avg_yards
FROM {{ ref('fact_play_matchup') }}
WHERE play_type = 'run' AND rusher_player_id IS NOT NULL
GROUP BY rusher_player_id, rusher_player_name, defteam, season,
         def_package, coverage_shell

UNION ALL

SELECT
    passer_player_id                                AS player_id,
    passer_player_name                              AS player_name,
    'QB'                                            AS role,
    defteam,
    season,
    def_package,
    coverage_shell,
    COUNT(*)                                        AS attempts,
    SUM(COALESCE(complete_pass, 0))                 AS completions,
    SUM(COALESCE(passing_yards, 0))                 AS yards,
    SUM(COALESCE(touchdown, 0))                     AS tds,
    SUM(COALESCE(interception, 0))                  AS interceptions,
    AVG(epa)                                        AS avg_epa,
    AVG(yards_gained)                               AS avg_yards
FROM {{ ref('fact_play_matchup') }}
WHERE play_type = 'pass' AND passer_player_id IS NOT NULL
GROUP BY passer_player_id, passer_player_name, defteam, season,
         def_package, coverage_shell
