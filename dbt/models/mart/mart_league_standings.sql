{{ config(alias='league_standings', materialized='table') }}

-- Standings for every 2026 Sleeper league: one row per manager per league.
-- Queries the sleeper schema directly (per design, these tables are not dbt
-- sources routed through raw). scoring_type and total_rosters ride along so
-- the /leagues API endpoint can serve league summaries from this one mart on
-- Neon, where the sleeper schema does not exist.

SELECT
    r.league_id,
    l.name                              AS league_name,
    l.season,
    l.status,
    l.scoring_type,
    l.total_rosters,
    r.roster_id,
    u.display_name                      AS manager_name,
    u.user_id,
    r.wins,
    r.losses,
    r.ties,
    r.fpts + (r.fpts_decimal / 100.0)                   AS total_points,
    r.fpts_against + (r.fpts_against_decimal / 100.0)   AS total_points_against,
    RANK() OVER (
        PARTITION BY r.league_id
        ORDER BY r.wins DESC, (r.fpts + r.fpts_decimal / 100.0) DESC
    ) AS standing
FROM sleeper.roster r
JOIN sleeper.league l ON r.league_id = l.league_id
JOIN sleeper.[user] u ON r.owner_id = u.user_id AND r.league_id = u.league_id
WHERE l.season = 2026
