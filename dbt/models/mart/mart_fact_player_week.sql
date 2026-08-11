-- mart_fact_player_week.sql
{{ config(alias='fact_player_week') }}

-- Power BI fact table. One row per player per week.
-- Contains raw stat measures only — fantasy points are calculated in DAX
-- using the disconnected dim_scoring_format table.

SELECT
    -- Keys for PBI relationships
    f.gsis_id,
    f.game_id,
    f.recent_team,
    f.opponent_team,
    (f.season * 100) + f.week               AS week_key,

    -- Degenerate dimensions (useful for labels/tooltips without joining)
    f.display_name,
    f.season,
    f.week,
    f.season_type,
    f.position,
    f.position_group,

    -- Passing measures
    f.completions,
    f.attempts,
    f.passing_yards,
    f.passing_tds,
    f.interceptions,
    f.sacks,
    f.sack_yards,
    f.sack_fumbles_lost,
    f.passing_air_yards,
    f.passing_yac,
    f.passing_first_downs,
    f.passing_epa,
    f.passing_2pt_conversions,

    -- Rushing measures
    f.carries,
    f.rushing_yards,
    f.rushing_tds,
    f.rushing_fumbles_lost,
    f.rushing_first_downs,
    f.rushing_epa,
    f.rushing_2pt_conversions,

    -- Receiving measures
    f.receptions,
    f.targets,
    f.receiving_yards,
    f.receiving_tds,
    f.receiving_fumbles_lost,
    f.receiving_air_yards,
    f.receiving_yac,
    f.receiving_first_downs,
    f.receiving_epa,
    f.receiving_2pt_conversions,

    -- Usage / share
    f.target_share,
    f.air_yards_share,
    f.wopr,

    -- Special teams
    f.special_teams_tds,

    -- Defensive raw stats
    f.def_tackles_solo,
    f.def_tackles_with_assist,
    f.def_tackle_assists,
    f.def_tackles_for_loss,
    f.def_fumbles_forced,
    f.def_sacks,
    f.def_sack_yards,
    f.def_qb_hits,
    f.def_interceptions,
    f.def_interception_yards,
    f.def_pass_defended,
    f.def_tds,
    f.def_fumbles,
    f.def_safeties,

    -- Computed defensive metrics
    ISNULL(f.def_tackles_solo, 0) + ISNULL(f.def_tackle_assists, 0)
                                             AS def_total_tackles,
    ISNULL(f.def_sacks, 0) + ISNULL(f.def_interceptions, 0)
        + ISNULL(f.def_fumbles_forced, 0) + ISNULL(f.def_tackles_for_loss, 0)
                                             AS def_playmaker_plays,
    ISNULL(f.def_qb_hits, 0) + ISNULL(f.def_sacks, 0)
                                             AS def_pressures,
    ISNULL(f.def_pass_defended, 0) + ISNULL(f.def_interceptions, 0)
                                             AS def_coverage_plays,

    -- Pre-computed combined fields (saves DAX complexity)
    ISNULL(f.sack_fumbles_lost, 0)
        + ISNULL(f.rushing_fumbles_lost, 0)
        + ISNULL(f.receiving_fumbles_lost, 0)
                                             AS total_fumbles_lost,

    ISNULL(f.passing_2pt_conversions, 0)
        + ISNULL(f.rushing_2pt_conversions, 0)
        + ISNULL(f.receiving_2pt_conversions, 0)
                                             AS total_2pt_conversions,

    -- Source fantasy points (validation only)
    f.source_fantasy_points,
    f.source_fantasy_points_ppr

FROM {{ ref('fact_player_week') }} f
