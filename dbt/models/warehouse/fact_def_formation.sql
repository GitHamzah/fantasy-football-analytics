-- fact_def_formation.sql
-- Defensive package tendencies: one row per DEFENSIVE team-season-package-
-- coverage shell combination.
--
-- Participation has no defensive-team column — possession_team is the
-- OFFENSE. The defense is derived through dim_game: whichever of home/away
-- is not in possession. The join is exact (nflverse_game_id is dim_game's
-- game_id) and was verified at 100% coverage with zero possession/home/away
-- mismatches across all five seasons.
--
-- avg_dl/avg_lb/avg_db ride along because a named package like "Nickel" spans
-- several fronts (4-2-5, 3-3-5, 2-4-5); the averages tell the UI which front
-- this team actually runs it from.
-- Materialized as a table in the warehouse schema.

SELECT
    CASE WHEN g.home_team = s.possession_team
         THEN g.away_team ELSE g.home_team END      AS team,
    s.season,
    s.def_personnel_grouping,
    s.coverage_shell,
    COUNT(*)                                        AS play_count,
    AVG(s.defenders_in_box)                         AS avg_box,
    AVG(CAST(s.def_dl_count AS FLOAT))              AS avg_dl,
    AVG(CAST(s.def_lb_count AS FLOAT))              AS avg_lb,
    AVG(CAST(s.def_db_count AS FLOAT))              AS avg_db
FROM {{ ref('stg_participation') }} s
JOIN {{ ref('dim_game') }} g
  ON g.game_id = s.nflverse_game_id
WHERE s.def_personnel_grouping IS NOT NULL
  AND s.possession_team IS NOT NULL
  AND s.possession_team <> ''
  -- Belt and braces: a possession abbreviation that matches neither side
  -- would silently mislabel the defense, so such rows are dropped instead.
  AND s.possession_team IN (g.home_team, g.away_team)
GROUP BY
    CASE WHEN g.home_team = s.possession_team
         THEN g.away_team ELSE g.home_team END,
    s.season, s.def_personnel_grouping, s.coverage_shell
