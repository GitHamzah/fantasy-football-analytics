{{ config(alias='season_projection', materialized='table') }}

-- Season totals of the scheme-adjusted weekly projections: one row per player.
-- Best/worst individual weeks are picked in the API from schedule_projection.

SELECT
    player_id,
    player_name,
    position,
    team,
    COUNT(*)                    AS projected_games,
    AVG(projected_yards)        AS avg_projected_yards,
    SUM(projected_yards)        AS total_projected_yards,
    SUM(projected_tds)          AS total_projected_tds,
    AVG(weighted_epa)           AS avg_epa,
    AVG(matchup_score)          AS avg_matchup_score,
    ppg_2025,
    targets_pg,
    carries_pg,
    volume_pg
FROM {{ ref('mart_schedule_projection') }}
GROUP BY player_id, player_name, position, team,
         ppg_2025, targets_pg, carries_pg, volume_pg
