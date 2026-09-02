{{ config(alias='schedule_projection', materialized='table') }}

-- Scheme-adjusted 2026 projections: one row per player per scheduled game.
-- The opponent's 2025 coverage-shell mix (2-High / 1-High / Loaded Box) weights
-- the player's 2025 per-shell production into a game-level projection. Shell
-- level only, deliberately - package x shell buckets are too thin to trust.
-- 2025 is the only usable tendency season: the 2022->2023 vocabulary break
-- makes older formation labels incomparable.
--
-- Fallbacks and choices beyond the sketch:
--   * A shell needs >= 5 attempts to count as a real split; where a player
--     lacks a shell, their OVERALL rate fills in (never 0, which would
--     silently deflate anyone with a thin split).
--   * matchup_score = scheme-weighted yds/att over the player's overall
--     yds/att, so > 1.0 reads "this schedule look suits them".
--   * Volume is targets+carries per game, plus pass attempts for QBs (their
--     production lives on dropbacks, not targets).
--   * The 2026 team comes from dim_player.current_team when known, falling
--     back to the 2025 team - traded players project onto their new schedule.

WITH schedule AS (
    SELECT g.season, g.week, g.home_team AS team, g.away_team AS opponent
    FROM {{ ref('dim_game') }} g
    WHERE g.season = 2026
    UNION ALL
    SELECT g.season, g.week, g.away_team AS team, g.home_team AS opponent
    FROM {{ ref('dim_game') }} g
    WHERE g.season = 2026
),

def_tendencies AS (
    SELECT
        team,
        coverage_shell,
        SUM(play_count) AS plays,
        CAST(SUM(play_count) AS FLOAT)
            / NULLIF(SUM(SUM(play_count)) OVER (PARTITION BY team), 0) AS shell_pct
    FROM {{ ref('mart_def_formation') }}
    WHERE season = 2025 AND coverage_shell IS NOT NULL
    GROUP BY team, coverage_shell
),

player_shells AS (
    SELECT
        player_id,
        coverage_shell,
        SUM(attempts) AS attempts,
        CAST(SUM(yards) AS FLOAT) / NULLIF(SUM(attempts), 0) AS yards_per_attempt,
        CAST(SUM(tds) AS FLOAT) / NULLIF(SUM(attempts), 0) AS td_rate,
        SUM(attempts * CAST(avg_epa AS FLOAT)) / NULLIF(SUM(attempts), 0) AS avg_epa
    FROM {{ ref('mart_player_vs_defense') }}
    WHERE season = 2025 AND coverage_shell IS NOT NULL
    GROUP BY player_id, coverage_shell
    HAVING SUM(attempts) >= 5
),

-- Schedule-neutral rates: the fallback for missing shells and the
-- denominator of matchup_score.
player_overall AS (
    SELECT
        player_id,
        CAST(SUM(yards) AS FLOAT) / NULLIF(SUM(attempts), 0) AS ypa,
        CAST(SUM(tds) AS FLOAT) / NULLIF(SUM(attempts), 0) AS td_rate,
        SUM(attempts * CAST(avg_epa AS FLOAT)) / NULLIF(SUM(attempts), 0) AS epa
    FROM {{ ref('mart_player_vs_defense') }}
    WHERE season = 2025
    GROUP BY player_id
    HAVING SUM(attempts) >= 5
),

player_baselines AS (
    SELECT
        f.gsis_id AS player_id,
        AVG(CAST(f.source_fantasy_points_ppr AS FLOAT)) AS ppg_2025,
        COUNT(*) AS games_2025,
        CAST(SUM(COALESCE(f.targets, 0)) AS FLOAT) / NULLIF(COUNT(*), 0) AS targets_pg,
        CAST(SUM(COALESCE(f.carries, 0)) AS FLOAT) / NULLIF(COUNT(*), 0) AS carries_pg,
        CAST(SUM(COALESCE(f.attempts, 0)) AS FLOAT) / NULLIF(COUNT(*), 0) AS pass_att_pg,
        MAX(f.position) AS position,
        MAX(f.display_name) AS player_name,
        MAX(f.recent_team) AS team_2025
    FROM {{ ref('fact_player_week') }} f
    WHERE f.season = 2025 AND f.season_type = 'REG'
      AND f.position IN ('QB', 'RB', 'WR', 'TE')
    GROUP BY f.gsis_id
    HAVING COUNT(*) >= 8
),

placed AS (
    SELECT
        pb.*,
        COALESCE(d.current_team, pb.team_2025) AS team,
        CASE WHEN pb.position = 'QB'
             THEN pb.pass_att_pg + pb.carries_pg
             ELSE pb.targets_pg + pb.carries_pg
        END AS volume_pg
    FROM player_baselines pb
    LEFT JOIN {{ ref('dim_player') }} d ON d.gsis_id = pb.player_id
)

SELECT
    pb.player_id,
    pb.player_name,
    pb.position,
    pb.team,
    s.week,
    s.opponent,
    pb.ppg_2025,
    pb.games_2025,
    pb.targets_pg,
    pb.carries_pg,
    pb.volume_pg,
    SUM(dt.shell_pct * COALESCE(ps.yards_per_attempt, po.ypa, 0)) * pb.volume_pg AS projected_yards,
    SUM(dt.shell_pct * COALESCE(ps.td_rate, po.td_rate, 0)) * pb.volume_pg      AS projected_tds,
    SUM(dt.shell_pct * COALESCE(ps.avg_epa, po.epa, 0))                          AS weighted_epa,
    SUM(dt.shell_pct * COALESCE(ps.yards_per_attempt, po.ypa, 0))
        / NULLIF(MAX(po.ypa), 0)                                                 AS matchup_score
FROM placed pb
JOIN schedule s ON pb.team = s.team
JOIN def_tendencies dt ON s.opponent = dt.team
LEFT JOIN player_overall po ON pb.player_id = po.player_id
LEFT JOIN player_shells ps
    ON pb.player_id = ps.player_id AND dt.coverage_shell = ps.coverage_shell
GROUP BY
    pb.player_id, pb.player_name, pb.position, pb.team,
    s.week, s.opponent,
    pb.ppg_2025, pb.games_2025, pb.targets_pg, pb.carries_pg, pb.volume_pg
