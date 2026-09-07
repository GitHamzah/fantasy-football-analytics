"""Matchup grading: 0-100 grades for players, position groups and teams.

Grades are percentile ranks against 2025 league distributions, so they are
relative by construction — a 75 means "better than 75% of qualifying players
at the position on this metric mix". League distributions are computed once
per process and cached (they only change when the warehouse reloads).

Data reality this leans on:
  * Offensive skill grades come from player_vs_defense (per-shell yards/att),
    fact_player_week (PPG, weekly volatility, boom rate).
  * Defensive grades come from mart.pfr_advstats, bridged to rosters by
    lowercase name + team (the same ~86%-coverage bridge the PFR endpoints
    already use). Defenders without PFR coverage grade at a neutral 50 with
    confidence "low" rather than being dropped.
  * There are no per-lineman PFR stats, so the OL grades as a unit: the
    inverse percentile of its own QB's pressure/sack rates.
  * The "scheme" component of a team defense grade is the inverse percentile
    of EPA/play allowed across all 32 defenses.
"""

import bisect
import re

from database import execute_query

GRADE_LABELS = [
    (90, "Elite"),
    (80, "Great"),
    (70, "Good"),
    (60, "Average"),
    (50, "Below Average"),
    (40, "Poor"),
    (0, "Terrible"),
]

# fact_player_week position code -> defensive bucket
DEF_BUCKET = {
    "DE": "DL", "DT": "DL", "NT": "DL", "DL": "DL",
    "LB": "LB", "MLB": "LB", "ILB": "LB", "OLB": "LB", "SLB": "LB", "WLB": "LB",
    "CB": "CB",
    "FS": "S", "SS": "S", "SAF": "S", "S": "S", "DB": "S",
}

SHELLS = ("2-High", "1-High", "Loaded Box")

_GSIS = re.compile(r"^00-\d{7}$")


def grade_label(g) -> str:
    if g is None:
        return "Unknown"
    for floor, label in GRADE_LABELS:
        if g >= floor:
            return label
    return "Terrible"


def pct(sorted_vals: list, v, invert: bool = False):
    """Percentile of v within a sorted list, 0-100. None-safe."""
    if v is None or not sorted_vals:
        return None
    p = 100.0 * bisect.bisect_left(sorted_vals, float(v)) / len(sorted_vals)
    p = min(100.0, max(0.0, p))
    return round(100.0 - p, 1) if invert else round(p, 1)


def _f(v):
    return float(v) if v is not None else None


# --------------------------------------------------------------------------
# League context (cached per season)
# --------------------------------------------------------------------------

_cache: dict = {}


def league_context(season: int = 2025) -> dict:
    if season in _cache:
        return _cache[season]

    ctx: dict = {"season": season}

    # ---- offensive per-player stats + distributions ----
    rows = execute_query("""
        SELECT
            f.gsis_id,
            MAX(f.position) AS pos,
            MAX(f.display_name) AS name,
            MAX(f.recent_team) AS team,
            AVG(CAST(f.source_fantasy_points_ppr AS FLOAT)) AS ppg,
            STDEV(CAST(f.source_fantasy_points_ppr AS FLOAT)) AS sd,
            SUM(CASE WHEN f.source_fantasy_points_ppr >= 20 THEN 1.0 ELSE 0 END)
                / COUNT(*) AS boom,
            COUNT(*) AS games
        FROM mart.fact_player_week f
        WHERE f.season = :season AND f.season_type = 'REG'
          AND f.position IN ('QB', 'RB', 'WR', 'TE')
        GROUP BY f.gsis_id
        HAVING COUNT(*) >= 8
    """, {"season": season})
    off = {}
    for r in rows:
        off[r["gsis_id"]] = {
            "pos": r["pos"], "name": r["name"], "team": r["team"],
            "ppg": _f(r["ppg"]), "sd": _f(r["sd"]), "boom": _f(r["boom"]),
        }
    ctx["off_stats"] = off

    ypa_rows = execute_query("""
        SELECT player_id,
               CAST(SUM(yards) AS FLOAT) / NULLIF(SUM(attempts), 0) AS ypa
        FROM mart.player_vs_defense
        WHERE season = :season
        GROUP BY player_id
        HAVING SUM(attempts) >= 30
    """, {"season": season})
    ypa = {r["player_id"]: _f(r["ypa"]) for r in ypa_rows}
    ctx["ypa"] = ypa

    dists: dict = {}
    for pid, s in off.items():
        d = dists.setdefault(s["pos"], {"ppg": [], "sd": [], "boom": [], "ypa": []})
        for k in ("ppg", "sd", "boom"):
            if s[k] is not None:
                d[k].append(s[k])
        if pid in ypa and ypa[pid] is not None:
            d["ypa"].append(ypa[pid])
    for d in dists.values():
        for k in d:
            d[k].sort()
    ctx["off_dists"] = dists

    # ---- defender PFR aggregates + bucket positions + distributions ----
    pfr = execute_query("""
        SELECT
            LOWER(p.pfr_player_name) AS lname,
            p.team,
            COUNT(DISTINCT p.week) AS games,
            AVG(CAST(p.def_completion_pct AS FLOAT)) AS comp_pct,
            AVG(CAST(p.def_yards_allowed_per_tgt AS FLOAT)) AS ypt,
            AVG(CAST(p.def_passer_rating_allowed AS FLOAT)) AS pra,
            SUM(COALESCE(p.def_targets, 0)) AS targets,
            SUM(COALESCE(p.def_ints, 0)) AS ints,
            SUM(COALESCE(p.def_sacks, 0)) AS sacks,
            SUM(COALESCE(p.def_pressures, 0)) AS pressures,
            AVG(CAST(p.def_missed_tackle_pct AS FLOAT)) AS mt_pct,
            SUM(COALESCE(p.def_tackles_combined, 0)) AS tackles
        FROM mart.pfr_advstats p
        WHERE p.season = :season
        GROUP BY LOWER(p.pfr_player_name), p.team
        HAVING COUNT(DISTINCT p.week) >= 6
    """, {"season": season})
    def_stats = {}
    for r in pfr:
        g = max(1, int(r["games"]))
        def_stats[(r["lname"], r["team"])] = {
            "games": g,
            "comp_pct": _f(r["comp_pct"]),
            "ypt": _f(r["ypt"]),
            "pra": _f(r["pra"]),
            "targets": int(r["targets"] or 0),
            "ints": int(r["ints"] or 0),
            "ints_pg": (r["ints"] or 0) / g,
            "sacks": _f(r["sacks"]) or 0.0,
            "sacks_pg": float(r["sacks"] or 0) / g,
            "pressures_pg": float(r["pressures"] or 0) / g,
            "mt_pct": _f(r["mt_pct"]),
            "tackles_pg": float(r["tackles"] or 0) / g,
        }
    ctx["def_stats"] = def_stats

    pos_rows = execute_query("""
        SELECT LOWER(f.display_name) AS lname, f.recent_team AS team,
               MAX(f.position) AS pos
        FROM mart.fact_player_week f
        WHERE f.season = :season
          AND f.position IN ('DE','DT','NT','DL','LB','MLB','ILB','OLB',
                             'CB','FS','SS','SAF','S','DB')
        GROUP BY LOWER(f.display_name), f.recent_team
    """, {"season": season})
    def_pos = {(r["lname"], r["team"]): DEF_BUCKET.get(r["pos"], "S") for r in pos_rows}
    ctx["def_pos"] = def_pos

    def_dists: dict = {b: {} for b in ("CB", "S", "LB", "DL")}
    for key, s in def_stats.items():
        bucket = def_pos.get(key)
        if bucket not in def_dists:
            continue
        for metric in ("comp_pct", "ypt", "pra", "ints_pg", "sacks_pg",
                       "pressures_pg", "mt_pct", "tackles_pg"):
            if s[metric] is not None:
                def_dists[bucket].setdefault(metric, []).append(float(s[metric]))
    for b in def_dists.values():
        for k in b:
            b[k].sort()
    ctx["def_dists"] = def_dists

    # ---- OL proxy: each team's QB pressure profile (lower = better OL) ----
    prs = execute_query("""
        SELECT f.recent_team AS team,
               AVG(CAST(p.times_pressured_pct AS FLOAT)) AS pressured_pct,
               SUM(COALESCE(p.times_sacked, 0)) * 1.0
                   / NULLIF(COUNT(DISTINCT p.week), 0) AS sacked_pg
        FROM mart.pfr_advstats p
        JOIN mart.fact_player_week f
          ON LOWER(f.display_name) = LOWER(p.pfr_player_name)
         AND f.recent_team = p.team AND f.season = p.season AND f.week = p.week
        WHERE p.season = :season AND f.position = 'QB'
        GROUP BY f.recent_team
    """, {"season": season})
    ctx["team_pressure"] = {r["team"]: (_f(r["pressured_pct"]), _f(r["sacked_pg"]))
                            for r in prs}
    ctx["pressure_dist"] = sorted(
        v[0] for v in ctx["team_pressure"].values() if v[0] is not None)

    # ---- scheme: EPA/play each defense allowed ----
    epa = execute_query("""
        SELECT defense_team AS team,
               SUM(plays * CAST(avg_epa AS FLOAT)) / NULLIF(SUM(plays), 0) AS epa
        FROM mart.team_matchup
        WHERE season = :season
        GROUP BY defense_team
    """, {"season": season})
    ctx["team_epa_allowed"] = {r["team"]: _f(r["epa"]) for r in epa}
    ctx["epa_dist"] = sorted(
        v for v in ctx["team_epa_allowed"].values() if v is not None)

    _cache[season] = ctx
    return ctx


# --------------------------------------------------------------------------
# Player grades
# --------------------------------------------------------------------------

def grade_offensive_player(player: dict, opp_shell_mix: dict, ctx: dict) -> dict:
    """Grade an offensive player against a specific defense's shell mix.

    player: {gsis_id, position, shells: {shell: (ypa, attempts)},
             overall_ypa, vs_def: {attempts, ypa} | None}
    opp_shell_mix: {shell: fraction summing to ~1}
    """
    pos = player["position"]
    dist = ctx["off_dists"].get(pos, {})
    stats = ctx["off_stats"].get(player["gsis_id"], {})
    overall = player.get("overall_ypa")

    # 40% scheme fit: shell-weighted yds/att, percentiled within position.
    scheme = None
    if opp_shell_mix and (player.get("shells") or overall is not None):
        weighted = 0.0
        for shell, frac in opp_shell_mix.items():
            s_ypa, s_att = player.get("shells", {}).get(shell, (None, 0))
            use = s_ypa if (s_ypa is not None and s_att >= 5) else overall
            if use is not None:
                weighted += frac * use
        scheme = pct(dist.get("ypa", []), weighted) if weighted else None

    # 25% production
    production = pct(dist.get("ppg", []), stats.get("ppg"))

    # 20% historical vs this exact defense (>=5 att), else the scheme score.
    vs_def = player.get("vs_def")
    if vs_def and vs_def.get("attempts", 0) >= 5 and vs_def.get("ypa") is not None:
        historical = pct(dist.get("ypa", []), vs_def["ypa"])
        hist_source = "head-to-head"
    else:
        historical = scheme
        hist_source = "scheme-fit"

    # 15% consistency: steadier weeks + boom rate.
    sd_p = pct(dist.get("sd", []), stats.get("sd"), invert=True)
    boom_p = pct(dist.get("boom", []), stats.get("boom"))
    consistency = (
        (sd_p + boom_p) / 2 if sd_p is not None and boom_p is not None
        else sd_p if sd_p is not None else boom_p
    )

    parts = [(scheme, 0.40), (production, 0.25), (historical, 0.20),
             (consistency, 0.15)]
    have = [(v, w) for v, w in parts if v is not None]
    if not have:
        return {"grade": None, "confidence": "none", "components": {}}
    total_w = sum(w for _, w in have)
    grade = round(sum(v * w for v, w in have) / total_w, 1)
    missing = 4 - len(have)
    return {
        "grade": grade,
        "confidence": "low" if missing >= 2 else "normal",
        "components": {
            "scheme_fit": scheme,
            "production": production,
            "historical": historical,
            "historical_source": hist_source,
            "consistency": consistency,
        },
    }


# metric -> (bucket applicability, invert) per defensive bucket
_DEF_METRICS = {
    "CB": [("comp_pct", True), ("ypt", True), ("pra", True), ("ints_pg", False)],
    "S":  [("comp_pct", True), ("ypt", True), ("pra", True), ("ints_pg", False),
           ("mt_pct", True)],
    "DL": [("sacks_pg", False), ("pressures_pg", False), ("mt_pct", True)],
    "LB": [("tackles_pg", False), ("mt_pct", True), ("comp_pct", True)],
}


def grade_defensive_player(name: str, team: str, bucket: str, ctx: dict) -> dict:
    """Grade a defender within their bucket from PFR percentiles."""
    key = ((name or "").lower(), team)
    s = ctx["def_stats"].get(key)
    if not s:
        return {"grade": 50.0, "confidence": "low", "pfr": None}

    dists = ctx["def_dists"].get(bucket, {})
    scores = []
    for metric, invert in _DEF_METRICS.get(bucket, []):
        p = pct(dists.get(metric, []), s.get(metric), invert=invert)
        if p is not None:
            scores.append(p)
    grade = round(sum(scores) / len(scores), 1) if scores else 50.0
    return {
        "grade": grade,
        "confidence": "normal" if len(scores) >= 2 else "low",
        # comp_pct / mt_pct are fractions in PFR; surfaced as percentages.
        "pfr": {
            "games": s["games"],
            "targets_allowed": s["targets"],
            "comp_pct_allowed": round(s["comp_pct"] * 100, 1) if s["comp_pct"] is not None else None,
            "yards_per_tgt": round(s["ypt"], 1) if s["ypt"] is not None else None,
            "passer_rating": round(s["pra"], 1) if s["pra"] is not None else None,
            "ints": s["ints"],
            "sacks": round(s["sacks"], 1),
            "pressures_pg": round(s["pressures_pg"], 1),
            "missed_tackle_pct": round(s["mt_pct"] * 100, 1) if s["mt_pct"] is not None else None,
            "tackles_pg": round(s["tackles_pg"], 1),
        },
    }


def ol_grade(team: str, ctx: dict) -> dict:
    """The OL as a unit: inverse percentile of its QB's pressure rate."""
    prs = ctx["team_pressure"].get(team)
    if not prs or prs[0] is None:
        return {"grade": 50.0, "confidence": "low"}
    return {
        "grade": pct(ctx["pressure_dist"], prs[0], invert=True) or 50.0,
        "confidence": "normal",
        # times_pressured_pct is a fraction in PFR; surfaced as a percentage.
        "pressured_pct": round(prs[0] * 100, 1),
        "sacked_pg": round(prs[1], 1) if prs[1] is not None else None,
    }


def scheme_grade(team: str, ctx: dict) -> float:
    """Defense-wide effectiveness: inverse percentile of EPA/play allowed."""
    epa = ctx["team_epa_allowed"].get(team)
    return pct(ctx["epa_dist"], epa, invert=True) or 50.0


# --------------------------------------------------------------------------
# Group and team rollups
# --------------------------------------------------------------------------

def grade_position_matchup(off_grades: list, def_grades: list) -> dict:
    """off/def group averages; matchup = off - def + 50 (50 = even)."""
    off_avg = round(sum(off_grades) / len(off_grades), 1) if off_grades else None
    def_avg = round(sum(def_grades) / len(def_grades), 1) if def_grades else None
    if off_avg is None or def_avg is None:
        return {"offense_grade": off_avg, "defense_grade": def_avg,
                "matchup": None, "edge": None, "advantage": "unknown"}
    edge = round((off_avg - def_avg) / 2, 1)  # halved: full grade gaps are rare
    matchup = round(min(100, max(0, off_avg - def_avg + 50)), 1)
    return {
        "offense_grade": off_avg,
        "defense_grade": def_avg,
        "matchup": matchup,
        "edge": edge,
        "advantage": "offense" if edge > 1 else "defense" if edge < -1 else "even",
    }


OFF_WEIGHTS = {"QB": 0.30, "WR": 0.30, "RB": 0.20, "TE": 0.10, "OL": 0.10}
DEF_WEIGHTS = {"CB": 0.30, "DL": 0.25, "LB": 0.20, "S": 0.15, "scheme": 0.10}


def weighted_grade(parts: dict, weights: dict):
    have = [(v, weights[k]) for k, v in parts.items()
            if v is not None and k in weights]
    if not have:
        return None
    return round(sum(v * w for v, w in have) / sum(w for _, w in have), 1)
