"""Game matchup analysis: team, position-group and player-level grades for any
pairing, built on the 2025 percentile distributions in services.matchup_grading.

Answers "how does BAL's offense match up against KC's defense at every level"
with graded rosters on both sides, six position-group matchups per direction,
formation context and 2025 head-to-head history.

Rosters are reused from routers.formations (same starters logic the formation
visuals use); player splits are batched per team (one IN-list query per kind)
rather than per player.
"""

import datetime as dt

from fastapi import APIRouter, HTTPException, Query
from database import execute_query
from routers.formations import get_def_formation_roster, get_formation_roster
from services.matchup_grading import (
    _GSIS,
    SHELLS,
    grade_defensive_player,
    grade_label,
    grade_offensive_player,
    grade_position_matchup,
    league_context,
    ol_grade,
    scheme_grade,
    weighted_grade,
    DEF_WEIGHTS,
    OFF_WEIGHTS,
)

router = APIRouter(prefix="/games", tags=["Game Matchups"])

STAT_SEASON = 2025  # all grading evidence comes from the completed season


def _f(v, digits=2):
    return round(float(v), digits) if v is not None else None


def _in_list(ids: list[str]) -> str:
    """Literal IN-list of validated GSIS ids (execute_query has no array binds)."""
    safe = [i for i in ids if i and _GSIS.match(i)]
    if not safe:
        return "('')"
    return "(" + ",".join(f"'{i}'" for i in safe) + ")"


# --------------------------------------------------------------------------
# Batched data helpers
# --------------------------------------------------------------------------

def _shell_mixes(teams: list[str]) -> dict[str, dict[str, float]]:
    """Each defense's 2025 coverage-shell mix as fractions."""
    rows = execute_query(f"""
        SELECT team, coverage_shell, SUM(play_count) AS plays
        FROM mart.def_formation
        WHERE season = {STAT_SEASON} AND coverage_shell IS NOT NULL
          AND team IN ({",".join("'" + t + "'" for t in teams)})
        GROUP BY team, coverage_shell
    """)
    totals: dict[str, int] = {}
    for r in rows:
        totals[r["team"]] = totals.get(r["team"], 0) + int(r["plays"])
    out: dict[str, dict[str, float]] = {}
    for r in rows:
        out.setdefault(r["team"], {})[r["coverage_shell"]] = (
            int(r["plays"]) / totals[r["team"]]
        )
    return out


def _player_shells(ids: list[str]) -> dict[str, dict[str, tuple]]:
    """Per player: {shell: (ypa, attempts)} from 2025 splits."""
    rows = execute_query(f"""
        SELECT player_id, coverage_shell,
               SUM(attempts) AS att,
               CAST(SUM(yards) AS FLOAT) / NULLIF(SUM(attempts), 0) AS ypa
        FROM mart.player_vs_defense
        WHERE season = {STAT_SEASON} AND coverage_shell IS NOT NULL
          AND player_id IN {_in_list(ids)}
        GROUP BY player_id, coverage_shell
    """)
    out: dict[str, dict[str, tuple]] = {}
    for r in rows:
        out.setdefault(r["player_id"], {})[r["coverage_shell"]] = (
            float(r["ypa"]) if r["ypa"] is not None else None,
            int(r["att"]),
        )
    return out


def _players_vs_team(ids: list[str], defteam: str) -> dict[str, dict]:
    """Per player: 2025 totals against one specific defense."""
    rows = execute_query(f"""
        SELECT player_id,
               SUM(attempts) AS att,
               SUM(COALESCE(yards, 0)) AS yards,
               SUM(COALESCE(tds, 0)) AS tds,
               CAST(SUM(yards) AS FLOAT) / NULLIF(SUM(attempts), 0) AS ypa
        FROM mart.player_vs_defense
        WHERE season = {STAT_SEASON} AND defteam = :defteam
          AND player_id IN {_in_list(ids)}
        GROUP BY player_id
    """, {"defteam": defteam})
    return {
        r["player_id"]: {
            "attempts": int(r["att"]),
            "yards": _f(r["yards"], 0),
            "tds": int(r["tds"]),
            "avg_yards": _f(r["ypa"], 1),
            "ypa": float(r["ypa"]) if r["ypa"] is not None else None,
        }
        for r in rows
    }


def _formation_context(teams: list[str]) -> dict[str, dict]:
    """Top offensive formation/personnel and top defensive package per team."""
    tl = ",".join("'" + t + "'" for t in teams)
    off = execute_query(f"""
        SELECT team, formation, SUM(play_count) AS plays
        FROM mart.formation WHERE season = {STAT_SEASON} AND team IN ({tl})
        GROUP BY team, formation
    """)
    pers = execute_query(f"""
        SELECT team, personnel_grouping, SUM(play_count) AS plays
        FROM mart.formation
        WHERE season = {STAT_SEASON} AND team IN ({tl})
          AND personnel_grouping IS NOT NULL
        GROUP BY team, personnel_grouping
    """)
    pkg = execute_query(f"""
        SELECT team, def_personnel_grouping AS pkg, SUM(play_count) AS plays
        FROM mart.def_formation WHERE season = {STAT_SEASON} AND team IN ({tl})
        GROUP BY team, def_personnel_grouping
    """)

    def top(rows, team, key):
        mine = [r for r in rows if r["team"] == team]
        total = sum(int(r["plays"]) for r in mine)
        if not mine:
            return None, None
        best = max(mine, key=lambda r: int(r["plays"]))
        return best[key], round(100.0 * int(best["plays"]) / total, 1)

    out = {}
    for t in teams:
        f_, f_pct = top(off, t, "formation")
        p_, _ = top(pers, t, "personnel_grouping")
        k_, k_pct = top(pkg, t, "pkg")
        out[t] = {
            "offense": {"top_formation": f_, "pct": f_pct, "top_personnel": p_},
            "defense": {"top_package": k_, "pct": k_pct},
        }
    return out


def _head_to_head(home: str, away: str) -> dict:
    games = execute_query("""
        SELECT COUNT(*) AS n FROM mart.dim_game
        WHERE season = :season
          AND ((home_team = :h AND away_team = :a)
            OR (home_team = :a AND away_team = :h))
    """, {"season": STAT_SEASON, "h": home, "a": away})
    n_games = int(games[0]["n"]) if games else 0

    rows = execute_query("""
        SELECT offense_team, coverage_shell,
               SUM(plays) AS plays,
               SUM(plays * CAST(avg_yards AS FLOAT)) / NULLIF(SUM(plays), 0) AS avg_yards,
               SUM(plays * CAST(avg_epa AS FLOAT)) / NULLIF(SUM(plays), 0) AS avg_epa
        FROM mart.team_matchup
        WHERE season = :season
          AND ((offense_team = :h AND defense_team = :a)
            OR (offense_team = :a AND defense_team = :h))
        GROUP BY offense_team, coverage_shell
    """, {"season": STAT_SEASON, "h": home, "a": away})

    def side(off_team):
        mine = [r for r in rows if r["offense_team"] == off_team]
        plays = sum(int(r["plays"]) for r in mine)
        if not plays:
            return None
        w = lambda k: sum(
            float(r[k]) * int(r["plays"]) for r in mine if r[k] is not None
        ) / plays
        return {
            "plays": plays,
            "avg_yards": round(w("avg_yards"), 1),
            "avg_epa": round(w("avg_epa"), 3),
            "by_shell": [
                {
                    "shell": r["coverage_shell"],
                    "plays": int(r["plays"]),
                    "avg_yards": _f(r["avg_yards"], 1),
                    "avg_epa": _f(r["avg_epa"], 3),
                }
                for r in sorted(mine, key=lambda r: -int(r["plays"]))
                if r["coverage_shell"] is not None
            ],
        }

    if n_games == 0:
        return {"games_played_2025": 0, "note": "no prior meetings in 2025"}
    return {
        "games_played_2025": n_games,
        "home_off_vs_away_def": side(home),
        "away_off_vs_home_def": side(away),
    }


# --------------------------------------------------------------------------
# Side builder: one offense vs one defense -> six graded position groups
# --------------------------------------------------------------------------

# offensive position -> which defender buckets contest it
GROUPS = [
    ("WR vs CB", ["WR"], ["CB"]),
    ("TE vs LB/S", ["TE"], ["LB2", "S"]),   # LB2 = top-2 coverage LBs
    ("RB vs Front 7", ["RB"], ["DL", "LB"]),
    ("QB vs Pass Rush", ["QB"], ["DL"]),
    ("QB vs Coverage", ["QB"], ["CB", "S"]),
    ("OL vs DL", ["OL"], ["DL"]),
]


def _grade_side(off_team: str, def_team: str, shell_mix: dict, ctx: dict,
                roster_season: int = STAT_SEASON) -> list[dict]:
    # Rosters follow the requested season (2026 falls back to current team
    # assignments); every grading stat still comes from STAT_SEASON.
    off_roster = get_formation_roster(team=off_team, season=roster_season)["players"]
    def_roster = get_def_formation_roster(team=def_team, season=roster_season)["players"]

    skill_ids = [
        p["player_id"]
        for pos in ("QB", "RB", "WR", "TE")
        for p in off_roster.get(pos, [])
    ]
    shells = _player_shells(skill_ids)
    vs_def = _players_vs_team(skill_ids, def_team)

    # Grade every offensive skill player once.
    off_graded: dict[str, list[dict]] = {}
    for pos in ("QB", "RB", "WR", "TE"):
        for p in off_roster.get(pos, []):
            pid = p["player_id"]
            g = grade_offensive_player(
                {
                    "gsis_id": pid,
                    "position": pos,
                    "shells": shells.get(pid, {}),
                    "overall_ypa": ctx["ypa"].get(pid),
                    "vs_def": vs_def.get(pid),
                },
                shell_mix,
                ctx,
            )
            stats = ctx["off_stats"].get(pid, {})
            entry = {
                "name": p["name"],
                "gsis_id": pid,
                "grade": g["grade"],
                "grade_label": grade_label(g["grade"]),
                "confidence": g["confidence"],
                "ppg": _f(stats.get("ppg"), 1),
                "vs_this_defense": (
                    {k: vs_def[pid][k] for k in ("attempts", "yards", "tds", "avg_yards")}
                    if pid in vs_def else None
                ),
                "vs_defense_shell": {
                    shell: {"attempts": att, "avg_yards": _f(ypa, 1)}
                    for shell, (ypa, att) in shells.get(pid, {}).items()
                },
            }
            off_graded.setdefault(pos, []).append(entry)

    # Grade every defender once.
    def_graded: dict[str, list[dict]] = {}
    for bucket in ("DL", "LB", "CB", "S"):
        for p in def_roster.get(bucket, []):
            g = grade_defensive_player(p["name"], def_team, bucket, ctx)
            def_graded.setdefault(bucket, []).append({
                "name": p["name"],
                "gsis_id": p["player_id"],
                "position": p["position"],
                "grade": g["grade"],
                "grade_label": grade_label(g["grade"]),
                "confidence": g["confidence"],
                "pfr": g["pfr"],
            })

    ol = ol_grade(off_team, ctx)

    def def_pick(spec: str) -> list[dict]:
        if spec == "LB2":
            return def_graded.get("LB", [])[:2]
        return def_graded.get(spec, [])

    results = []
    for group_name, off_specs, def_specs in GROUPS:
        if off_specs == ["OL"]:
            off_players = [
                {"name": p["name"], "gsis_id": p["player_id"],
                 "position": p.get("position"), "grade": None}
                for p in off_roster.get("OL", [])
            ]
            off_grades = [ol["grade"]]
            group_off_note = ol
        else:
            off_players = [p for pos in off_specs for p in off_graded.get(pos, [])]
            off_grades = [p["grade"] for p in off_players if p["grade"] is not None]
            group_off_note = None

        def_players = [p for spec in def_specs for p in def_pick(spec)]
        def_grades = [p["grade"] for p in def_players if p["grade"] is not None]

        m = grade_position_matchup(off_grades, def_grades)
        results.append({
            "group": group_name,
            "offense_team": off_team,
            "defense_team": def_team,
            **m,
            "insight": _insight(group_name, off_team, def_team, m, def_players, group_off_note),
            "offense_players": off_players,
            "defense_players": def_players,
        })
    return results


def _avg(vals):
    vals = [v for v in vals if v is not None]
    return sum(vals) / len(vals) if vals else None


def _insight(group, off_team, def_team, m, def_players, ol_note) -> str:
    """One line per group, anchored to an actual stat when one exists."""
    og, dg = m["offense_grade"], m["defense_grade"]
    adv_def = m["advantage"] == "defense"
    pfr = [p["pfr"] for p in def_players if p.get("pfr")]

    if group == "WR vs CB" and pfr:
        comp = _avg([p["comp_pct_allowed"] for p in pfr])
        if comp is not None:
            tone = "tough sledding for" if adv_def else "a matchup to attack for"
            return (f"{def_team}'s corners allow a {comp:.1f}% completion rate — "
                    f"{tone} {off_team}'s receivers.")
    if group == "QB vs Pass Rush" and pfr:
        prs = _avg([p["pressures_pg"] for p in pfr])
        if prs is not None:
            return (f"{def_team}'s line averages {prs:.1f} pressures per game per "
                    f"rusher — {'a real problem' if adv_def else 'manageable heat'} "
                    f"for {off_team}'s dropbacks.")
    if group == "RB vs Front 7" and pfr:
        mt = _avg([p["missed_tackle_pct"] for p in pfr])
        if mt is not None:
            return (f"{def_team}'s front misses {mt:.1f}% of tackles — "
                    f"{'little room' if adv_def else 'yards after contact available'} "
                    f"for {off_team}'s backs.")
    if group == "QB vs Coverage" and pfr:
        pra = _avg([p["passer_rating"] for p in pfr])
        if pra is not None:
            return (f"{def_team}'s secondary allows a {pra:.1f} passer rating — "
                    f"{'a stingy back end' if adv_def else 'throwing windows exist'} "
                    f"for {off_team}.")
    if group == "TE vs LB/S" and pfr:
        ypt = _avg([p["yards_per_tgt"] for p in pfr])
        if ypt is not None:
            return (f"{def_team}'s second level allows {ypt:.1f} yds/target in "
                    f"coverage — the seam is "
                    f"{'closed' if adv_def else 'open'} for {off_team}'s tight ends.")
    if group == "OL vs DL" and ol_note and ol_note.get("pressured_pct") is not None:
        return (f"{off_team}'s line let its QB be pressured on "
                f"{ol_note['pressured_pct']:.1f}% of dropbacks in 2025 — "
                f"{'trouble' if adv_def else 'holding up'} against {def_team}'s rush.")
    return (f"{def_team}'s unit (grade {dg}) "
            f"{'has the edge over' if adv_def else 'gives ground to'} "
            f"{off_team}'s (grade {og}).")


def _team_summary(home, away, home_groups, away_groups, ctx) -> dict:
    def offense_grade(groups):
        by = {g["group"]: g["offense_grade"] for g in groups}
        qb = _avg([by.get("QB vs Pass Rush"), by.get("QB vs Coverage")])
        return weighted_grade(
            {"QB": qb, "WR": by.get("WR vs CB"), "RB": by.get("RB vs Front 7"),
             "TE": by.get("TE vs LB/S"), "OL": by.get("OL vs DL")},
            OFF_WEIGHTS,
        )

    def defense_grade(groups, def_team):
        buckets: dict[str, list] = {}
        for g in groups:
            for p in g["defense_players"]:
                b = p["position"]
                from services.matchup_grading import DEF_BUCKET
                buckets.setdefault(DEF_BUCKET.get(b, "S"), []).append(p["grade"])
        parts = {b: _avg(v) for b, v in buckets.items()}
        parts["scheme"] = scheme_grade(def_team, ctx)
        return weighted_grade(parts, DEF_WEIGHTS)

    home_off = offense_grade(home_groups)
    away_def = defense_grade(home_groups, away)
    away_off = offense_grade(away_groups)
    home_def = defense_grade(away_groups, home)

    # Headline: the single most lopsided group either way.
    all_groups = home_groups + away_groups
    scored = [g for g in all_groups if g["edge"] is not None]
    headline = "An even matchup across the board."
    if scored:
        top = max(scored, key=lambda g: abs(g["edge"]))
        winner = top["defense_team"] if top["edge"] < 0 else top["offense_team"]
        side = ("defense holds the edge" if top["edge"] < 0
                else "offense holds the edge")
        headline = (f"{winner}'s {side} — {top['group']} is the most lopsided "
                    f"unit battle ({top['edge']:+.1f}).")

    return {
        "home_offense_grade": home_off,
        "home_offense_label": grade_label(home_off),
        "away_defense_grade": away_def,
        "away_defense_label": grade_label(away_def),
        "home_edge": round((home_off - away_def) / 2, 1)
                     if home_off is not None and away_def is not None else None,
        "away_offense_grade": away_off,
        "away_offense_label": grade_label(away_off),
        "home_defense_grade": home_def,
        "home_defense_label": grade_label(home_def),
        "away_edge": round((away_off - home_def) / 2, 1)
                     if away_off is not None and home_def is not None else None,
        "headline": headline,
    }


# --------------------------------------------------------------------------
# Endpoints
# --------------------------------------------------------------------------

@router.get("/week")
def get_week_games(
    season: int = Query(2026, description="Season year"),
    week: int = Query(1, ge=1, le=22),
):
    """All games in one week, from the schedule."""
    rows = execute_query("""
        SELECT game_id, home_team, away_team, gameday, gametime
        FROM mart.dim_game
        WHERE season = :season AND week = :week
        ORDER BY gameday, gametime
    """, {"season": season, "week": week})
    if not rows:
        raise HTTPException(404, f"No games for {season} week {week}")

    def weekday(d):
        try:
            return dt.date.fromisoformat(str(d)[:10]).strftime("%A")
        except (ValueError, TypeError):
            return None

    return {
        "season": season,
        "week": week,
        "games": [
            {
                "game_id": r["game_id"],
                "home_team": r["home_team"],
                "away_team": r["away_team"],
                "gameday": str(r["gameday"])[:10] if r["gameday"] else None,
                "weekday": weekday(r["gameday"]),
                "gametime": r["gametime"],
            }
            for r in rows
        ],
    }


@router.get("/matchup")
def get_game_matchup(
    home: str = Query(..., description="Home team abbreviation"),
    away: str = Query(..., description="Away team abbreviation"),
    season: int = Query(2026, description="Season (grading always uses 2025 data)"),
):
    """The flagship: full two-way matchup grades for one game."""
    home, away = home.upper(), away.upper()
    ctx = league_context(STAT_SEASON)
    mixes = _shell_mixes([home, away])
    if home not in mixes or away not in mixes:
        missing = [t for t in (home, away) if t not in mixes]
        raise HTTPException(404, f"No defensive tendency data for {missing}")

    try:
        home_groups = _grade_side(home, away, mixes[away], ctx, roster_season=season)
        away_groups = _grade_side(away, home, mixes[home], ctx, roster_season=season)
    except HTTPException as e:
        raise HTTPException(404, f"Roster data missing: {e.detail}")

    fc = _formation_context([home, away])
    shell_pcts = lambda t: {
        s: round(100 * f, 1) for s, f in mixes.get(t, {}).items()
    }

    return {
        "home_team": home,
        "away_team": away,
        "season": season,
        "stats_season": STAT_SEASON,
        "matchup_summary": _team_summary(home, away, home_groups, away_groups, ctx),
        "position_matchups": home_groups + away_groups,
        "formation_context": {
            "home_offense": fc[home]["offense"],
            "home_defense": {**fc[home]["defense"], "shells": shell_pcts(home)},
            "away_offense": fc[away]["offense"],
            "away_defense": {**fc[away]["defense"], "shells": shell_pcts(away)},
        },
        "head_to_head": _head_to_head(home, away),
    }


# offensive position -> the defender buckets they primarily face
_COUNTERPART = {"WR": ["CB", "S"], "TE": ["LB", "S"], "RB": ["DL", "LB"],
                "QB": ["CB", "S"]}


@router.get("/player-vs-look")
def get_player_vs_look(
    player_id: str = Query(..., description="GSIS player id"),
    season: int = Query(2025),
    def_package: str | None = Query(None),
    coverage_shell: str | None = Query(None),
    defteam: str | None = Query(None, description="Also list this defense's relevant starters"),
):
    """One player against one defensive look, broken down by opponent."""
    if not def_package and not coverage_shell:
        raise HTTPException(400, "Provide def_package and/or coverage_shell")

    where = "WHERE p.player_id = :pid AND p.season = :season"
    params: dict = {"pid": player_id, "season": season}
    if def_package:
        where += " AND p.def_package = :pkg"
        params["pkg"] = def_package
    if coverage_shell:
        where += " AND p.coverage_shell = :shell"
        params["shell"] = coverage_shell

    rows = execute_query(f"""
        SELECT p.player_name, p.role, p.defteam,
               SUM(p.attempts) AS att,
               SUM(COALESCE(p.yards, 0)) AS yards,
               SUM(COALESCE(p.tds, 0)) AS tds,
               SUM(p.attempts * CAST(p.avg_epa AS FLOAT))
                   / NULLIF(SUM(p.attempts), 0) AS epa
        FROM mart.player_vs_defense p
        {where}
        GROUP BY p.player_name, p.role, p.defteam
        ORDER BY SUM(p.attempts) DESC
    """, params)
    if not rows:
        raise HTTPException(404, "No data for that player and look")

    total_att = sum(int(r["att"]) for r in rows)
    total_yards = sum(float(r["yards"] or 0) for r in rows)

    out = {
        "player_id": player_id,
        "player_name": rows[0]["player_name"],
        "season": season,
        "def_package": def_package,
        "coverage_shell": coverage_shell,
        "totals": {
            "attempts": total_att,
            "yards": round(total_yards, 0),
            "tds": sum(int(r["tds"]) for r in rows),
            "avg_yards": round(total_yards / total_att, 1) if total_att else None,
        },
        "by_opponent": [
            {
                "defteam": r["defteam"],
                "attempts": int(r["att"]),
                "yards": _f(r["yards"], 0),
                "tds": int(r["tds"]),
                "avg_yards": _f(
                    float(r["yards"] or 0) / int(r["att"]) if int(r["att"]) else None, 1),
                "avg_epa": _f(r["epa"], 3),
            }
            for r in rows
        ],
    }

    if defteam:
        defteam = defteam.upper()
        ctx = league_context(STAT_SEASON)
        try:
            roster = get_def_formation_roster(team=defteam, season=STAT_SEASON)["players"]
        except HTTPException:
            roster = {}
        # Which defenders matter for this player's position group.
        pos_rows = execute_query(
            "SELECT position FROM mart.dim_player WHERE gsis_id = :pid",
            {"pid": player_id})
        pos = pos_rows[0]["position"] if pos_rows else "WR"
        defenders = []
        for bucket in _COUNTERPART.get(pos, ["CB", "S"]):
            for p in roster.get(bucket, []):
                g = grade_defensive_player(p["name"], defteam, bucket, ctx)
                defenders.append({
                    "name": p["name"], "position": p["position"],
                    "grade": g["grade"], "grade_label": grade_label(g["grade"]),
                    "pfr": g["pfr"],
                })
        out["opposing_defenders"] = {"defteam": defteam, "players": defenders}

    return out
