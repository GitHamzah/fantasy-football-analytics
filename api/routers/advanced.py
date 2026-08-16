"""Advanced stats endpoints — team defense quality and PFR advanced metrics.

These expose two mart tables that had no HTTP surface: mart.team_defense and
mart.pfr_advstats. PFR is keyed on pfr_player_id, which does not relate to
gsis_id, so player-level lookups bridge through fact_player_week on
name + team + season + week (~86% of player-weeks match).
"""

from fastapi import APIRouter, Query
from database import execute_query

router = APIRouter(prefix="/advanced", tags=["Advanced"])


# Defensive position groups, using the codes that actually appear in the data.
_SECONDARY = "('CB', 'DB', 'SAF', 'FS', 'SS', 'S')"
_FRONT_SEVEN = "('DE', 'DT', 'NT', 'DL', 'LB', 'OLB', 'ILB', 'MLB')"


@router.get("/team-defense")
def get_team_defense(
    season: int = Query(..., description="Season year"),
):
    """Team defensive quality metrics, one row per team.

    Sourced from mart.team_defense — per-game pressure, coverage and
    playmaking rates aggregated from individual defensive player stats.
    Used for DST streaming decisions.
    """
    return execute_query("""
        SELECT
            t.team,
            t.season,
            t.games,
            t.sacks_pg,
            t.qb_hits_pg,
            t.interceptions_pg,
            t.pass_defended_pg,
            t.fumbles_forced_pg,
            t.tfl_pg,
            t.pressure_pg,
            t.coverage_pg,
            t.playmaker_pg,
            CAST(COALESCE(t.sacks_pg, 0)
               + COALESCE(t.interceptions_pg, 0)
               + COALESCE(t.fumbles_forced_pg, 0) AS DECIMAL(10,2)) AS dst_score
        FROM mart.team_defense t
        WHERE t.season = :season
        ORDER BY dst_score DESC
    """, {"season": season})


@router.get("/pfr/player/{player_id}")
def get_player_advanced(
    player_id: str,
    season: int | None = Query(None, description="Limit to a single season"),
):
    """Pro Football Reference advanced metrics for one player, by season.

    Returns an empty list when the player has no PFR coverage — the feeds only
    include players with meaningful snap counts.
    """
    where = "WHERE f.gsis_id = :player_id AND f.season_type = 'REG'"
    params: dict = {"player_id": player_id}
    if season:
        where += " AND f.season = :season"
        params["season"] = season

    return execute_query(f"""
        SELECT
            f.season,
            f.display_name                                      AS player_name,
            f.position,
            f.recent_team                                       AS team,
            COUNT(*)                                            AS games,

            -- Passing
            CAST(AVG(p.passing_bad_throw_pct) AS DECIMAL(10,2))  AS bad_throw_pct,
            CAST(AVG(p.times_pressured_pct) AS DECIMAL(10,2))    AS pressured_pct,
            CAST(AVG(p.times_blitzed) AS DECIMAL(10,2))          AS blitzed_pg,
            CAST(AVG(p.times_hurried) AS DECIMAL(10,2))          AS hurried_pg,
            CAST(AVG(p.times_hit) AS DECIMAL(10,2))              AS hit_pg,
            CAST(AVG(p.times_sacked) AS DECIMAL(10,2))           AS sacked_pg,

            -- Rushing
            CAST(AVG(p.rushing_yards_before_contact_avg) AS DECIMAL(10,2)) AS ybc_per_carry,
            CAST(AVG(p.rushing_yards_after_contact_avg) AS DECIMAL(10,2))  AS yac_per_carry,
            CAST(AVG(p.rushing_broken_tackles) AS DECIMAL(10,2))           AS broken_tackles_pg,

            -- Receiving
            CAST(AVG(p.receiving_drop_pct) AS DECIMAL(10,2))     AS drop_pct,
            CAST(AVG(p.receiving_rat) AS DECIMAL(10,2))          AS target_passer_rating,
            CAST(AVG(p.receiving_broken_tackles) AS DECIMAL(10,2)) AS rec_broken_tackles_pg
        FROM mart.fact_player_week f
        JOIN mart.pfr_advstats p
          ON LOWER(p.pfr_player_name) = LOWER(f.display_name)
         AND p.team = f.recent_team
         AND p.season = f.season
         AND p.week = f.week
        {where}
        GROUP BY f.season, f.display_name, f.position, f.recent_team
        ORDER BY f.season
    """, params)


@router.get("/pfr/defense-vs-position")
def get_defense_by_unit(
    season: int = Query(..., description="Season year"),
    unit: str | None = Query(None, description="SECONDARY or FRONT7"),
):
    """PFR defensive metrics aggregated by team and defensive unit.

    SECONDARY backs the coverage view a WR matchup needs; FRONT7 backs the
    run-stopping and pass-rush views RBs and QBs need. Position comes from
    fact_player_week, since the PFR feed carries no position column.
    """
    where = ""
    params: dict = {"season": season}
    if unit and unit.upper() in ("SECONDARY", "FRONT7"):
        where = "AND u.unit = :unit"
        params["unit"] = unit.upper()

    return execute_query(f"""
        WITH joined AS (
            SELECT
                p.team,
                p.season,
                p.week,
                CASE
                    WHEN f.position IN {_SECONDARY}   THEN 'SECONDARY'
                    WHEN f.position IN {_FRONT_SEVEN} THEN 'FRONT7'
                    ELSE 'OTHER'
                END                                             AS unit,
                p.def_targets,
                p.def_completion_pct,
                p.def_yards_allowed_per_tgt,
                p.def_passer_rating_allowed,
                p.def_ints,
                p.def_sacks,
                p.def_pressures,
                p.def_times_hitqb,
                p.def_tackles_combined,
                p.def_missed_tackle_pct
            FROM mart.pfr_advstats p
            JOIN mart.fact_player_week f
              ON LOWER(f.display_name) = LOWER(p.pfr_player_name)
             AND f.recent_team = p.team
             AND f.season = p.season
             AND f.week = p.week
            WHERE p.season = :season
              AND f.season_type = 'REG'
        ),
        u AS (SELECT * FROM joined WHERE unit <> 'OTHER')
        SELECT
            u.team                                              AS defense,
            u.unit,
            COUNT(DISTINCT u.week)                              AS games,

            -- Coverage (meaningful for SECONDARY)
            CAST(AVG(u.def_completion_pct) AS DECIMAL(10,2))     AS completion_pct_allowed,
            CAST(AVG(u.def_yards_allowed_per_tgt) AS DECIMAL(10,2)) AS yards_per_target_allowed,
            CAST(AVG(u.def_passer_rating_allowed) AS DECIMAL(10,2)) AS passer_rating_allowed,
            CAST(SUM(COALESCE(u.def_targets, 0)) * 1.0
                / NULLIF(COUNT(DISTINCT u.week), 0) AS DECIMAL(10,2)) AS targets_pg,
            CAST(SUM(COALESCE(u.def_ints, 0)) * 1.0
                / NULLIF(COUNT(DISTINCT u.week), 0) AS DECIMAL(10,2)) AS ints_pg,

            -- Pass rush and tackling (meaningful for FRONT7)
            CAST(SUM(COALESCE(u.def_sacks, 0)) * 1.0
                / NULLIF(COUNT(DISTINCT u.week), 0) AS DECIMAL(10,2)) AS sacks_pg,
            CAST(SUM(COALESCE(u.def_pressures, 0)) * 1.0
                / NULLIF(COUNT(DISTINCT u.week), 0) AS DECIMAL(10,2)) AS pressures_pg,
            CAST(SUM(COALESCE(u.def_times_hitqb, 0)) * 1.0
                / NULLIF(COUNT(DISTINCT u.week), 0) AS DECIMAL(10,2)) AS qb_hits_pg,
            CAST(SUM(COALESCE(u.def_tackles_combined, 0)) * 1.0
                / NULLIF(COUNT(DISTINCT u.week), 0) AS DECIMAL(10,2)) AS tackles_pg,
            CAST(AVG(u.def_missed_tackle_pct) AS DECIMAL(10,2))  AS missed_tackle_pct
        FROM u
        WHERE 1 = 1 {where}
        GROUP BY u.team, u.unit
        ORDER BY u.unit, u.team
    """, params)
