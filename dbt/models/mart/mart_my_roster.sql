{{ config(alias='my_roster', materialized='table') }}

-- Hamzah's current-season Sleeper rosters joined to the analytics engine:
-- 2025 fantasy production from fact_player_week and best/worst coverage-shell
-- matchups from player_vs_defense. Specifically scoped to his user id and the
-- 2026 season; generalizing to any user means dropping the two filters.
--
-- Deviations from the sketch, deliberate:
--   * fact_player_week's PPR column is source_fantasy_points_ppr.
--   * The shell ranking aggregates to (player, shell) BEFORE ranking. Ranking
--     the mart's raw rows would crown a single defteam-package-shell slice
--     (one 40-yard target vs one defense) as the "best shell".
--
-- Synced to Neon as a flat table; the sleeper schema itself never leaves
-- SQL Server.

WITH shell_agg AS (
    SELECT
        player_id,
        coverage_shell,
        SUM(CAST(yards AS FLOAT)) / NULLIF(SUM(attempts), 0) AS avg_yards,
        SUM(attempts) AS attempts
    FROM {{ ref('mart_player_vs_defense') }}
    WHERE season = 2025 AND coverage_shell IS NOT NULL
    GROUP BY player_id, coverage_shell
    HAVING SUM(attempts) >= 5
),

shell_ranked AS (
    SELECT *,
        ROW_NUMBER() OVER (PARTITION BY player_id ORDER BY avg_yards DESC) AS rn_best,
        ROW_NUMBER() OVER (PARTITION BY player_id ORDER BY avg_yards ASC)  AS rn_worst
    FROM shell_agg
),

pw AS (
    SELECT
        gsis_id,
        season,
        AVG(CAST(source_fantasy_points_ppr AS FLOAT)) AS ppg,
        COUNT(*) AS games_played,
        SUM(COALESCE(passing_yards, 0) + COALESCE(rushing_yards, 0)
            + COALESCE(receiving_yards, 0)) AS total_yards,
        SUM(COALESCE(passing_tds, 0) + COALESCE(rushing_tds, 0)
            + COALESCE(receiving_tds, 0)) AS total_tds
    FROM {{ ref('fact_player_week') }}
    WHERE season_type = 'REG'
    GROUP BY gsis_id, season
)

SELECT
    sr.league_id,
    sr.league_name,
    sr.league_status,
    sr.roster_id,
    sr.manager_name,
    sr.owner_id,
    sr.sleeper_id,
    sr.gsis_id,
    sr.player_name,
    sr.position,
    sr.team,
    sr.is_starter,
    sr.season,
    pw.ppg,
    pw.games_played,
    pw.total_yards,
    pw.total_tds,
    best_shell.coverage_shell   AS best_shell,
    best_shell.avg_yards        AS best_shell_avg_yards,
    worst_shell.coverage_shell  AS worst_shell,
    worst_shell.avg_yards       AS worst_shell_avg_yards
FROM {{ ref('stg_sleeper_roster') }} sr
LEFT JOIN pw
    ON sr.gsis_id = pw.gsis_id AND pw.season = 2025
LEFT JOIN shell_ranked best_shell
    ON sr.gsis_id = best_shell.player_id AND best_shell.rn_best = 1
LEFT JOIN shell_ranked worst_shell
    ON sr.gsis_id = worst_shell.player_id AND worst_shell.rn_worst = 1
WHERE sr.season = 2026
  AND sr.owner_id = '997944313776496640'
