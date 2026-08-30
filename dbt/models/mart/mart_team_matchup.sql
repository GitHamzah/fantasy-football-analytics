{{ config(alias='team_matchup', materialized='table') }}

-- Offense vs defense by package and shell: one row per offense-defense-season-
-- package-shell. Backs the "how does DAL move the ball against PHI's nickel"
-- style of question. Materialized as a table so Neon sync reads it.

SELECT
    posteam                                         AS offense_team,
    defteam                                         AS defense_team,
    season,
    def_package,
    coverage_shell,
    COUNT(*)                                        AS plays,
    SUM(CASE WHEN play_type = 'pass' THEN 1 ELSE 0 END) AS pass_plays,
    SUM(CASE WHEN play_type = 'run'  THEN 1 ELSE 0 END) AS run_plays,
    AVG(yards_gained)                               AS avg_yards,
    SUM(COALESCE(touchdown, 0))                     AS touchdowns,
    AVG(epa)                                        AS avg_epa,
    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END)    AS successful_plays
FROM {{ ref('fact_play_matchup') }}
WHERE posteam IS NOT NULL AND defteam IS NOT NULL
GROUP BY posteam, defteam, season, def_package, coverage_shell
