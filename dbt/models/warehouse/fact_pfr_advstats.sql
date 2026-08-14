-- fact_pfr_advstats.sql
-- Unified Pro Football Reference advanced stats: one row per player per week,
-- combining the passing, rushing, receiving and defensive stat types.
--
-- The four PFR feeds each cover a different population (only passers appear in
-- pfr_pass, only defenders in pfr_def), so the grain is built from the union of
-- keys across all four rather than from any single table. A player who only
-- rushed gets NULLs in the passing/receiving/defensive columns.
--
-- Note: pfr_player_id is PFR's own identifier and does NOT join to gsis_id.
-- Bridging to fact_player_week requires a name/team/week match or a crosswalk.
-- Materialized as a table in the warehouse schema.

WITH keys AS (
    SELECT pfr_player_id, season, week FROM {{ ref('stg_pfr_pass') }}
    UNION
    SELECT pfr_player_id, season, week FROM {{ ref('stg_pfr_rush') }}
    UNION
    SELECT pfr_player_id, season, week FROM {{ ref('stg_pfr_rec') }}
    UNION
    SELECT pfr_player_id, season, week FROM {{ ref('stg_pfr_def') }}
)

SELECT
    k.pfr_player_id,
    k.season,
    k.week,

    -- Descriptors: identical across feeds, take the first non-null
    COALESCE(p.pfr_player_name, ru.pfr_player_name,
             re.pfr_player_name, d.pfr_player_name)        AS pfr_player_name,
    COALESCE(p.game_id, ru.game_id, re.game_id, d.game_id) AS game_id,
    COALESCE(p.game_type, ru.game_type,
             re.game_type, d.game_type)                    AS game_type,
    COALESCE(p.team, ru.team, re.team, d.team)             AS team,
    COALESCE(p.opponent, ru.opponent,
             re.opponent, d.opponent)                      AS opponent,

    -- Passing (from pfr_pass)
    p.passing_drops,
    p.passing_drop_pct,
    p.passing_bad_throws,
    p.passing_bad_throw_pct,
    p.times_sacked,
    p.times_blitzed,
    p.times_hurried,
    p.times_hit,
    p.times_pressured,
    p.times_pressured_pct,

    -- Rushing (from pfr_rush). Aliased to avoid colliding with the
    -- nflverse `carries` column on fact_player_week.
    ru.carries                                             AS pfr_carries,
    ru.rushing_yards_before_contact,
    ru.rushing_yards_before_contact_avg,
    ru.rushing_yards_after_contact,
    ru.rushing_yards_after_contact_avg,
    ru.rushing_broken_tackles,

    -- Receiving (from pfr_rec)
    re.receiving_broken_tackles,
    re.receiving_drop,
    re.receiving_drop_pct,
    re.receiving_int,
    re.receiving_rat,

    -- Defensive coverage (from pfr_def)
    d.def_ints,
    d.def_targets,
    d.def_completions_allowed,
    d.def_completion_pct,
    d.def_yards_allowed,
    d.def_yards_allowed_per_cmp,
    d.def_yards_allowed_per_tgt,
    d.def_receiving_td_allowed,
    d.def_passer_rating_allowed,
    d.def_adot,
    d.def_air_yards_completed,
    d.def_yards_after_catch,

    -- Defensive pass rush and tackling (from pfr_def)
    d.def_times_blitzed,
    d.def_times_hurried,
    d.def_times_hitqb,
    d.def_sacks,
    d.def_pressures,
    d.def_tackles_combined,
    d.def_missed_tackles,
    d.def_missed_tackle_pct

FROM keys k
LEFT JOIN {{ ref('stg_pfr_pass') }} p
       ON p.pfr_player_id = k.pfr_player_id
      AND p.season = k.season
      AND p.week = k.week
LEFT JOIN {{ ref('stg_pfr_rush') }} ru
       ON ru.pfr_player_id = k.pfr_player_id
      AND ru.season = k.season
      AND ru.week = k.week
LEFT JOIN {{ ref('stg_pfr_rec') }} re
       ON re.pfr_player_id = k.pfr_player_id
      AND re.season = k.season
      AND re.week = k.week
LEFT JOIN {{ ref('stg_pfr_def') }} d
       ON d.pfr_player_id = k.pfr_player_id
      AND d.season = k.season
      AND d.week = k.week
