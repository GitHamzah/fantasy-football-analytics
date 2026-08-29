-- fact_formation.sql
-- Team formation and personnel tendencies: one row per team-season-formation-
-- personnel grouping combination.
--
-- Participation carries no play_type, so pass/run splits are deliberately
-- absent — adding them means joining raw pbp on nflverse_game_id + play_id in
-- staging first. play_count and defenders_in_box are what the feed supports.
--
-- personnel_grouping is NULL for 2023+ rows that failed offense validation in
-- staging (~14% of the feed); those plays still count toward formation totals
-- as their own NULL-grouping row rather than being dropped.
-- Materialized as a table in the warehouse schema.

SELECT
    s.possession_team                               AS team,
    s.season,
    s.offense_formation                             AS formation,
    s.personnel_grouping,
    COUNT(*)                                        AS play_count,
    AVG(s.defenders_in_box)                         AS avg_defenders_in_box
FROM {{ ref('stg_participation') }} s
WHERE s.possession_team IS NOT NULL
  AND s.possession_team <> ''
GROUP BY s.possession_team, s.season, s.offense_formation, s.personnel_grouping
