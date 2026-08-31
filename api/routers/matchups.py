"""Matchup analysis endpoints: player and team performance split by the
defensive look faced (personnel package and coverage shell).

Backed by mart.player_vs_defense and mart.team_matchup. Both marts live on
Neon too, so every query goes through execute_query and every numeric is cast
to int/float before it reaches the response (psycopg2 returns Decimal).

Mart schema note: player_vs_defense uses ONE stat schema across roles rather
than per-role columns — attempts means targets/carries/dropbacks and yards
means receiving/rushing/passing depending on the role column. The response
builders translate those into role-appropriate key names (targets, carries,
dropbacks, ...).

player_name in the mart is the pbp short form ("A.Pierce"); display names come
from dim_player via gsis_id.

Averages recombine by weighting on attempts: each mart row's avg_epa/avg_yards
is an average over that row's plays, so SUM(attempts * avg) / SUM(attempts)
reproduces the true play-level average at any rollup.
"""

from fastapi import APIRouter, HTTPException, Query
from database import execute_query

router = APIRouter(prefix="/matchups", tags=["Matchups"])


# Response key for the attempt count, per role.
_ATTEMPT_KEY = {"WR/TE": "targets", "RB": "carries", "QB": "dropbacks"}
# Response key for completions, per role (RB has none).
_COMPLETION_KEY = {"WR/TE": "receptions", "QB": "completions"}
# dim_player position -> mart role, for the position filter.
_POSITION_ROLE = {"WR": "WR/TE", "TE": "WR/TE", "RB": "RB", "FB": "RB", "QB": "QB"}


def _f(v, digits=2):
    return round(float(v), digits) if v is not None else None


def _stat_block(role: str, att, comp, yards, tds, avg_epa, avg_yards) -> dict:
    """One split's stats with role-appropriate key names."""
    out = {
        _ATTEMPT_KEY.get(role, "plays"): int(att or 0),
        "yards": _f(yards, 1),
        "tds": int(tds or 0),
        "avg_yards": _f(avg_yards, 1),
        "avg_epa": _f(avg_epa, 3),
        "plays": int(att or 0),
    }
    ckey = _COMPLETION_KEY.get(role)
    if ckey:
        out[ckey] = int(comp or 0)
    return out


def _player_detail(player_id: str, season: int, role: str, defteam: str | None = None):
    """Package x shell detail for one player-season, summed across defenses
    (or filtered to one), with play-weighted averages."""
    where = "WHERE p.player_id = :pid AND p.season = :season AND p.role = :role"
    params: dict = {"pid": player_id, "season": season, "role": role}
    if defteam:
        where += " AND p.defteam = :defteam"
        params["defteam"] = defteam

    return execute_query(f"""
        SELECT
            p.def_package,
            p.coverage_shell,
            SUM(p.attempts)                     AS att,
            SUM(COALESCE(p.completions, 0))     AS comp,
            SUM(COALESCE(p.yards, 0))           AS yards,
            SUM(COALESCE(p.tds, 0))             AS tds,
            SUM(p.attempts * p.avg_epa)
              / NULLIF(SUM(p.attempts), 0)      AS avg_epa,
            SUM(p.attempts * p.avg_yards)
              / NULLIF(SUM(p.attempts), 0)      AS avg_yards
        FROM mart.player_vs_defense p
        {where}
        GROUP BY p.def_package, p.coverage_shell
    """, params)


def _rollup(detail: list[dict], key: str, role: str) -> list[dict]:
    """Collapse package x shell detail rows onto one dimension.

    NULL keys are dropped from the list (a NULL shell play still counted in
    the package rollup because the rollup runs over ALL detail rows, not just
    labeled ones — this is the 'include in totals, exclude from breakdown'
    rule from the spec).
    """
    groups: dict = {}
    for r in detail:
        k = r[key]
        if k is None:
            continue
        g = groups.setdefault(k, {"att": 0, "comp": 0, "yards": 0.0, "tds": 0,
                                  "epa_w": 0.0, "yds_w": 0.0, "w": 0})
        att = int(r["att"] or 0)
        g["att"] += att
        g["comp"] += int(r["comp"] or 0)
        g["yards"] += float(r["yards"] or 0)
        g["tds"] += int(r["tds"] or 0)
        if r["avg_epa"] is not None:
            g["epa_w"] += float(r["avg_epa"]) * att
            g["w"] += att
        if r["avg_yards"] is not None:
            g["yds_w"] += float(r["avg_yards"]) * att

    out = []
    for k, g in groups.items():
        block = _stat_block(
            role, g["att"], g["comp"], g["yards"], g["tds"],
            g["epa_w"] / g["w"] if g["w"] else None,
            g["yds_w"] / g["w"] if g["w"] else None,
        )
        out.append({key: k, **block})
    out.sort(key=lambda r: r["plays"], reverse=True)
    return out


def _player_header(player_id: str) -> dict | None:
    rows = execute_query("""
        SELECT d.gsis_id, d.display_name, d.position, d.current_team
        FROM mart.dim_player d
        WHERE d.gsis_id = :pid
    """, {"pid": player_id})
    return rows[0] if rows else None


def _dominant_role(player_id: str, season: int, defteam: str | None = None) -> str | None:
    where = "WHERE player_id = :pid AND season = :season"
    params: dict = {"pid": player_id, "season": season}
    if defteam:
        where += " AND defteam = :defteam"
        params["defteam"] = defteam
    rows = execute_query(f"""
        SELECT role, SUM(attempts) AS att
        FROM mart.player_vs_defense
        {where}
        GROUP BY role
        ORDER BY SUM(attempts) DESC
    """, params)
    return rows[0]["role"] if rows else None


@router.get("/player/{player_id}")
def get_player_matchups(
    player_id: str,
    season: int = Query(..., description="Season year"),
):
    """A player's splits by defensive package and coverage shell.

    Stats come from the player's dominant role that season (an RB also shows
    up as a receiver in the mart; the role with the most opportunities wins).
    """
    role = _dominant_role(player_id, season)
    if role is None:
        raise HTTPException(404, f"No matchup data for player {player_id} in {season}")

    detail = _player_detail(player_id, season, role)
    header = _player_header(player_id)

    return {
        "player_id": player_id,
        "player_name": header["display_name"] if header else None,
        "position": header["position"] if header else None,
        "team": header["current_team"] if header else None,
        "season": season,
        "role": role,
        "by_package": _rollup(detail, "def_package", role),
        "by_shell": _rollup(detail, "coverage_shell", role),
        "by_package_and_shell": sorted(
            [
                {
                    "def_package": r["def_package"],
                    "coverage_shell": r["coverage_shell"],
                    **_stat_block(role, r["att"], r["comp"], r["yards"], r["tds"],
                                  r["avg_epa"], r["avg_yards"]),
                }
                for r in detail
                if r["def_package"] is not None and r["coverage_shell"] is not None
            ],
            key=lambda r: r["plays"],
            reverse=True,
        ),
    }


@router.get("/player/{player_id}/vs-team")
def get_player_vs_team(
    player_id: str,
    defteam: str = Query(..., description="Defensive team abbreviation"),
    season: int = Query(..., description="Season year"),
):
    """One player against one defense, broken by scheme."""
    defteam = defteam.upper()
    role = _dominant_role(player_id, season, defteam)
    if role is None:
        raise HTTPException(
            404, f"No matchup data for player {player_id} vs {defteam} in {season}")

    detail = _player_detail(player_id, season, role, defteam)
    header = _player_header(player_id)

    # Season-vs-team totals across every row, labeled or not.
    att = sum(int(r["att"] or 0) for r in detail)
    w = sum(int(r["att"] or 0) for r in detail if r["avg_epa"] is not None)
    epa = (
        sum(float(r["avg_epa"]) * int(r["att"] or 0)
            for r in detail if r["avg_epa"] is not None) / w
        if w else None
    )
    yds_w = (
        sum(float(r["avg_yards"]) * int(r["att"] or 0)
            for r in detail if r["avg_yards"] is not None) / w
        if w else None
    )
    total = _stat_block(
        role, att,
        sum(int(r["comp"] or 0) for r in detail),
        sum(float(r["yards"] or 0) for r in detail),
        sum(int(r["tds"] or 0) for r in detail),
        epa, yds_w,
    )

    return {
        "player_id": player_id,
        "player_name": header["display_name"] if header else None,
        "position": header["position"] if header else None,
        "vs_team": defteam,
        "season": season,
        "role": role,
        "total": total,
        "by_package": _rollup(detail, "def_package", role),
        "by_shell": _rollup(detail, "coverage_shell", role),
    }


@router.get("/team")
def get_team_matchup(
    offense: str = Query(..., description="Offensive team abbreviation"),
    defense: str = Query(..., description="Defensive team abbreviation"),
    season: int = Query(..., description="Season year"),
):
    """One offense against one defense, broken by scheme."""
    offense, defense = offense.upper(), defense.upper()

    rows = execute_query("""
        SELECT
            t.def_package,
            t.coverage_shell,
            SUM(t.plays)                        AS plays,
            SUM(t.pass_plays)                   AS pass_plays,
            SUM(t.run_plays)                    AS run_plays,
            SUM(COALESCE(t.touchdowns, 0))      AS touchdowns,
            SUM(t.successful_plays)             AS successful_plays,
            SUM(t.plays * t.avg_yards) / NULLIF(SUM(t.plays), 0) AS avg_yards,
            SUM(t.plays * t.avg_epa)   / NULLIF(SUM(t.plays), 0) AS avg_epa
        FROM mart.team_matchup t
        WHERE t.offense_team = :offense AND t.defense_team = :defense
          AND t.season = :season
        GROUP BY t.def_package, t.coverage_shell
    """, {"offense": offense, "defense": defense, "season": season})

    if not rows:
        raise HTTPException(
            404, f"No matchup data for {offense} vs {defense} in {season}")

    def agg(subset):
        plays = sum(int(r["plays"]) for r in subset)
        passes = sum(int(r["pass_plays"] or 0) for r in subset)
        runs = sum(int(r["run_plays"] or 0) for r in subset)
        succ = sum(int(r["successful_plays"] or 0) for r in subset)
        tds = sum(int(r["touchdowns"] or 0) for r in subset)
        w = sum(int(r["plays"]) for r in subset if r["avg_epa"] is not None)
        return {
            "plays": plays,
            "pass_plays": passes,
            "run_plays": runs,
            "pass_rate": round(100.0 * passes / plays, 1) if plays else 0.0,
            "success_rate": round(100.0 * succ / plays, 1) if plays else 0.0,
            "touchdowns": tds,
            "avg_yards": _f(
                sum(float(r["avg_yards"]) * int(r["plays"])
                    for r in subset if r["avg_yards"] is not None) / w if w else None, 1),
            "avg_epa": _f(
                sum(float(r["avg_epa"]) * int(r["plays"])
                    for r in subset if r["avg_epa"] is not None) / w if w else None, 3),
        }

    def group(key):
        seen: dict = {}
        for r in rows:
            if r[key] is None:
                continue
            seen.setdefault(r[key], []).append(r)
        out = [{key: k, **agg(v)} for k, v in seen.items()]
        out.sort(key=lambda r: r["plays"], reverse=True)
        return out

    overall = agg(rows)
    return {
        "offense": offense,
        "defense": defense,
        "season": season,
        "total_plays": overall["plays"],
        "overall": overall,
        "by_package": group("def_package"),
        "by_shell": group("coverage_shell"),
    }


@router.get("/top-performers")
def get_top_performers(
    season: int = Query(..., description="Season year"),
    def_package: str | None = Query(None, description="e.g. Nickel, Dime, 4-3 Base"),
    coverage_shell: str | None = Query(None, description="2-High, 1-High or Loaded Box"),
    position: str | None = Query(None, description="WR, TE, RB or QB"),
    limit: int = Query(20, ge=1, le=100),
    min_attempts: int = Query(20, ge=1, description="Floor to filter out flukes"),
):
    """Players with the most production against a specific defensive look."""
    if not def_package and not coverage_shell:
        raise HTTPException(400, "Provide def_package and/or coverage_shell")

    where = "WHERE p.season = :season"
    params: dict = {"season": season, "min_attempts": min_attempts}
    if def_package:
        where += " AND p.def_package = :def_package"
        params["def_package"] = def_package
    if coverage_shell:
        where += " AND p.coverage_shell = :coverage_shell"
        params["coverage_shell"] = coverage_shell

    role = None
    if position:
        role = _POSITION_ROLE.get(position.upper())
        if role is None:
            raise HTTPException(400, f"Unknown position {position}")
        where += " AND p.role = :role AND d.position = :position"
        params["role"] = role
        params["position"] = position.upper()

    rows = execute_query(f"""
        SELECT
            p.player_id,
            COALESCE(d.display_name, p.player_name) AS player_name,
            d.current_team                          AS team,
            p.role,
            SUM(p.attempts)                         AS att,
            SUM(COALESCE(p.completions, 0))         AS comp,
            SUM(COALESCE(p.yards, 0))               AS yards,
            SUM(COALESCE(p.tds, 0))                 AS tds,
            SUM(p.attempts * p.avg_epa)
              / NULLIF(SUM(p.attempts), 0)          AS avg_epa,
            SUM(p.attempts * p.avg_yards)
              / NULLIF(SUM(p.attempts), 0)          AS avg_yards
        FROM mart.player_vs_defense p
        LEFT JOIN mart.dim_player d ON d.gsis_id = p.player_id
        {where}
        GROUP BY p.player_id, COALESCE(d.display_name, p.player_name),
                 d.current_team, p.role
        HAVING SUM(p.attempts) >= :min_attempts
        ORDER BY SUM(COALESCE(p.yards, 0)) DESC
    """, params)

    players = [
        {
            "player_id": r["player_id"],
            "player_name": r["player_name"],
            "team": r["team"],
            "role": r["role"],
            **_stat_block(r["role"], r["att"], r["comp"], r["yards"], r["tds"],
                          r["avg_epa"], r["avg_yards"]),
        }
        for r in rows[:limit]
    ]

    return {
        "def_package": def_package,
        "coverage_shell": coverage_shell,
        "season": season,
        "position": position.upper() if position else None,
        "players": players,
    }
