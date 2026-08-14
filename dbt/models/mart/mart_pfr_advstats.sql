-- mart_pfr_advstats.sql
{{ config(alias='pfr_advstats') }}

-- Power BI / API view of Pro Football Reference advanced stats.
-- One row per player per week. Raw advanced measures only.
--
-- Keyed on pfr_player_id, which is PFR's identifier and does not relate to
-- gsis_id — this table is not directly joinable to fact_player_week.

SELECT
    -- Keys
    f.pfr_player_id,
    f.game_id,
    f.season,
    f.week,
    (f.season * 100) + f.week               AS week_key,

    -- Degenerate dimensions
    f.pfr_player_name,
    f.game_type,
    f.team,
    f.opponent,

    -- Passing measures
    f.passing_drops,
    f.passing_drop_pct,
    f.passing_bad_throws,
    f.passing_bad_throw_pct,
    f.times_sacked,
    f.times_blitzed,
    f.times_hurried,
    f.times_hit,
    f.times_pressured,
    f.times_pressured_pct,

    -- Rushing measures
    f.pfr_carries,
    f.rushing_yards_before_contact,
    f.rushing_yards_before_contact_avg,
    f.rushing_yards_after_contact,
    f.rushing_yards_after_contact_avg,
    f.rushing_broken_tackles,

    -- Receiving measures
    f.receiving_broken_tackles,
    f.receiving_drop,
    f.receiving_drop_pct,
    f.receiving_int,
    f.receiving_rat,

    -- Defensive coverage measures
    f.def_ints,
    f.def_targets,
    f.def_completions_allowed,
    f.def_completion_pct,
    f.def_yards_allowed,
    f.def_yards_allowed_per_cmp,
    f.def_yards_allowed_per_tgt,
    f.def_receiving_td_allowed,
    f.def_passer_rating_allowed,
    f.def_adot,
    f.def_air_yards_completed,
    f.def_yards_after_catch,

    -- Defensive pass rush and tackling measures
    f.def_times_blitzed,
    f.def_times_hurried,
    f.def_times_hitqb,
    f.def_sacks,
    f.def_pressures,
    f.def_tackles_combined,
    f.def_missed_tackles,
    f.def_missed_tackle_pct

FROM {{ ref('fact_pfr_advstats') }} f
