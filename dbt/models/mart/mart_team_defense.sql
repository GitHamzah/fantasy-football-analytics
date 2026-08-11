{{ config(alias='team_defense') }}

-- Team defensive quality metrics aggregated from individual player stats.
-- One row per team per season. Used for matchup analysis.

SELECT
    f.recent_team                                       AS team,
    f.season,
    COUNT(DISTINCT f.week)                              AS games,

    -- Aggregate defensive stats (sum across all defensive players per game, then average per game)
    CAST(SUM(ISNULL(f.def_sacks, 0)) * 1.0 / NULLIF(COUNT(DISTINCT f.week), 0) AS DECIMAL(10,1))
                                                        AS sacks_pg,
    CAST(SUM(ISNULL(f.def_qb_hits, 0)) * 1.0 / NULLIF(COUNT(DISTINCT f.week), 0) AS DECIMAL(10,1))
                                                        AS qb_hits_pg,
    CAST(SUM(ISNULL(f.def_interceptions, 0)) * 1.0 / NULLIF(COUNT(DISTINCT f.week), 0) AS DECIMAL(10,1))
                                                        AS interceptions_pg,
    CAST(SUM(ISNULL(f.def_pass_defended, 0)) * 1.0 / NULLIF(COUNT(DISTINCT f.week), 0) AS DECIMAL(10,1))
                                                        AS pass_defended_pg,
    CAST(SUM(ISNULL(f.def_fumbles_forced, 0)) * 1.0 / NULLIF(COUNT(DISTINCT f.week), 0) AS DECIMAL(10,1))
                                                        AS fumbles_forced_pg,
    CAST(SUM(ISNULL(f.def_tackles_for_loss, 0)) * 1.0 / NULLIF(COUNT(DISTINCT f.week), 0) AS DECIMAL(10,1))
                                                        AS tfl_pg,

    -- Composite scores
    CAST((SUM(ISNULL(f.def_sacks, 0)) + SUM(ISNULL(f.def_qb_hits, 0))) * 1.0
        / NULLIF(COUNT(DISTINCT f.week), 0) AS DECIMAL(10,1))
                                                        AS pressure_pg,
    CAST((SUM(ISNULL(f.def_pass_defended, 0)) + SUM(ISNULL(f.def_interceptions, 0))) * 1.0
        / NULLIF(COUNT(DISTINCT f.week), 0) AS DECIMAL(10,1))
                                                        AS coverage_pg,
    CAST((SUM(ISNULL(f.def_sacks, 0)) + SUM(ISNULL(f.def_interceptions, 0))
        + SUM(ISNULL(f.def_fumbles_forced, 0)) + SUM(ISNULL(f.def_tackles_for_loss, 0))) * 1.0
        / NULLIF(COUNT(DISTINCT f.week), 0) AS DECIMAL(10,1))
                                                        AS playmaker_pg

FROM {{ ref('fact_player_week') }} f
WHERE f.season_type = 'REG'
  AND f.position IN ('DL', 'LB', 'DB', 'DE', 'DT', 'NT', 'OLB', 'ILB', 'MLB', 'CB', 'FS', 'SS', 'S', 'SAF')
GROUP BY f.recent_team, f.season
