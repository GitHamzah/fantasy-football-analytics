"""Projection engine — builds fantasy projections for the upcoming season.

Prefers a trained scikit-learn model (see services/ml_projections.py). When no
model artifact is present — or the request asks for a scoring format the model
was not trained on — it falls back to the original weighted historical average
with age curves. Every projection carries a `method` field of "ml" or
"weighted_avg" so callers can tell which produced it.
"""

from database import execute_query
from datetime import date


# The ML model is trained on PPR scoring. Other formats fall back to the
# weighted average, which applies the requested reception value directly.
_ML_SCORING = "ppr"


# Age curve multipliers by position
# Based on general NFL aging curves — decline rates after peak
AGE_CURVES = {
    "QB": {(0, 25): 0.95, (25, 33): 1.00, (33, 36): 0.95, (36, 99): 0.88},
    "RB": {(0, 24): 0.97, (24, 27): 1.00, (27, 29): 0.92, (29, 31): 0.85, (31, 99): 0.75},
    "WR": {(0, 23): 0.95, (23, 30): 1.00, (30, 32): 0.93, (32, 99): 0.85},
    "TE": {(0, 24): 0.93, (24, 31): 1.00, (31, 33): 0.93, (33, 99): 0.85},
}


def _get_age_multiplier(position: str, age: int) -> float:
    """Get age curve multiplier for a player's position and age."""
    curves = AGE_CURVES.get(position, {(0, 99): 1.00})
    for (low, high), mult in curves.items():
        if low <= age < high:
            return mult
    return 1.00


def get_player_projections(
    target_season: int = 2026,
    scoring: str = "ppr",
    min_games: int = 6,
    limit: int = 150,
) -> list[dict]:
    """Generate fantasy projections for the target season.

    Uses the trained ML model when one is available and the request is for PPR
    scoring; otherwise falls back to the weighted-average engine. The response
    shape is identical either way, with `method` recording which was used.
    """
    if scoring == _ML_SCORING:
        try:
            from services.ml_projections import model_exists, predict_next_season

            if model_exists():
                ml_rows = predict_next_season(
                    target_season=target_season,
                    limit=limit,
                    min_games=min_games,
                )
                if ml_rows:
                    return _finalise(_to_projection_shape(ml_rows), limit)
        except Exception as e:
            import traceback
            print(f"ML projection failed, falling back to weighted average: {e}")
            traceback.print_exc()

    return _weighted_average_projections(target_season, scoring, min_games, limit)


def _to_projection_shape(ml_rows: list[dict]) -> list[dict]:
    """Map ml_projections output onto the engine's public response shape."""
    out = []
    for r in ml_rows:
        out.append({
            "player_id": r["player_id"],
            "player_name": r["player_name"],
            "position": r["position"],
            "team": r["team"],
            "age": r["age"],
            "projected_ppg": r["predicted_ppg"],
            "projected_games": r["predicted_games"],
            "projected_total": r["predicted_total"],
            # No age multiplier under the ML model — age is a model feature
            # rather than a post-hoc adjustment.
            "age_multiplier": None,
            "base_ppg": r["last_season_ppg"],
            "opportunities_pg": None,
            "last_season_ppg": r["last_season_ppg"],
            "last_season_games": r["last_season_games"],
            "seasons_of_data": None,
            "method": "ml",
        })
    return out


def _finalise(projections: list[dict], limit: int) -> list[dict]:
    """Sort, trim and attach overall/positional ranks."""
    projections.sort(key=lambda x: x["projected_total"], reverse=True)
    pos_counters: dict[str, int] = {}
    for i, p in enumerate(projections[:limit], 1):
        p["overall_rank"] = i
        pos = p["position"]
        pos_counters[pos] = pos_counters.get(pos, 0) + 1
        p["pos_rank"] = pos_counters[pos]
    return projections[:limit]


def _weighted_average_projections(
    target_season: int = 2026,
    scoring: str = "ppr",
    min_games: int = 6,
    limit: int = 150,
) -> list[dict]:
    """Original projection methodology, used when the ML model is unavailable.

    1. Weighted historical PPG (most recent season weighted highest)
    2. Age curve adjustment
    3. Games played projection based on historical availability
    4. Projected season total = adjusted PPG × projected games
    """
    ppr_value = {"standard": 0.0, "half_ppr": 0.5, "ppr": 1.0}.get(scoring, 1.0)
    current_year = target_season

    # Get last 3 seasons of per-game data for each player
    players = execute_query("""
        SELECT
            f.gsis_id,
            f.display_name,
            f.position,
            f.recent_team,
            f.season,
            COUNT(*)                                    AS games,
            CAST(AVG(
                COALESCE(f.passing_yards, 0) * 0.04
              + COALESCE(f.passing_tds, 0) * 4.0
              + COALESCE(f.interceptions, 0) * -2.0
              + COALESCE(f.rushing_yards, 0) * 0.1
              + COALESCE(f.rushing_tds, 0) * 6.0
              + COALESCE(f.receptions, 0) * :ppr
              + COALESCE(f.receiving_yards, 0) * 0.1
              + COALESCE(f.receiving_tds, 0) * 6.0
              + COALESCE(f.total_fumbles_lost, 0) * -2.0
              + COALESCE(f.total_2pt_conversions, 0) * 2.0
              + COALESCE(f.special_teams_tds, 0) * 6.0
            ) AS DECIMAL(10,2))                         AS ppg,
            CAST(AVG(COALESCE(f.targets, 0) + COALESCE(f.carries, 0))
                AS DECIMAL(10,1))                       AS opportunities_pg,
            CAST(AVG(COALESCE(f.targets, 0)) AS DECIMAL(10,1)) AS targets_pg,
            CAST(AVG(COALESCE(f.carries, 0)) AS DECIMAL(10,1)) AS carries_pg,
            CAST(AVG(COALESCE(f.receptions, 0)) AS DECIMAL(10,1)) AS receptions_pg
        FROM mart.fact_player_week f
        WHERE f.season BETWEEN :start_season AND :end_season
          AND f.season_type = 'REG'
          AND f.position IN ('QB', 'RB', 'WR', 'TE')
        GROUP BY f.gsis_id, f.display_name, f.position, f.recent_team, f.season
        HAVING COUNT(*) >= :min_games
    """, {
        "ppr": ppr_value,
        "start_season": target_season - 3,
        "end_season": target_season - 1,
        "min_games": min_games,
    })

    # Get player ages from dim_player
    ages = execute_query("""
        SELECT gsis_id, birth_date, current_team
        FROM mart.dim_player
        WHERE birth_date IS NOT NULL
    """)
    age_map = {}
    team_map = {}
    for row in ages:
        if row["birth_date"]:
            try:
                bd = row["birth_date"]
                if isinstance(bd, str):
                    bd = date.fromisoformat(bd)
                age_map[row["gsis_id"]] = current_year - bd.year
            except (ValueError, TypeError):
                pass
        if row["current_team"]:
            team_map[row["gsis_id"]] = row["current_team"]

    # Season weights (most recent = highest weight)
    s1 = target_season - 1  # e.g. 2025 → weight 0.60
    s2 = target_season - 2  # e.g. 2024 → weight 0.30
    s3 = target_season - 3  # e.g. 2023 → weight 0.10
    weights = {s1: 0.60, s2: 0.30, s3: 0.10}

    # Group by player
    player_seasons = {}
    for row in players:
        pid = row["gsis_id"]
        if pid not in player_seasons:
            player_seasons[pid] = {
                "player_id": pid,
                "player_name": row["display_name"],
                "position": row["position"],
                "team": team_map.get(pid, row["recent_team"]),
                "seasons": {},
            }
        player_seasons[pid]["seasons"][row["season"]] = row

    # Calculate projections
    projections = []
    for pid, info in player_seasons.items():
        seasons_data = info["seasons"]

        # Need at least the most recent season
        if s1 not in seasons_data:
            continue

        # Weighted PPG
        total_weight = 0
        weighted_ppg = 0
        weighted_opp = 0
        total_games = 0
        seasons_played = 0

        for szn, weight in weights.items():
            if szn in seasons_data:
                sd = seasons_data[szn]
                weighted_ppg += float(sd["ppg"]) * weight
                weighted_opp += float(sd["opportunities_pg"]) * weight
                total_weight += weight
                total_games += int(sd["games"])
                seasons_played += 1

        if total_weight == 0:
            continue

        base_ppg = weighted_ppg / total_weight
        base_opp = weighted_opp / total_weight

        # Games projection (average availability × 17 game season)
        avg_games_per_season = total_games / seasons_played
        projected_games = min(17, round(avg_games_per_season))

        # Age adjustment
        age = age_map.get(pid)
        age_mult = 1.0
        if age:
            age_mult = _get_age_multiplier(info["position"], age)

        projected_ppg = round(base_ppg * age_mult, 1)
        projected_total = round(projected_ppg * projected_games, 1)

        # Get most recent season stats for context
        latest = seasons_data[s1]

        projections.append({
            "player_id": pid,
            "player_name": info["player_name"],
            "position": info["position"],
            "team": info["team"],
            "age": age,
            "projected_ppg": projected_ppg,
            "projected_games": projected_games,
            "projected_total": projected_total,
            "age_multiplier": round(age_mult, 2),
            "base_ppg": round(base_ppg, 1),
            "opportunities_pg": round(base_opp, 1),
            "last_season_ppg": float(latest["ppg"]),
            "last_season_games": int(latest["games"]),
            "seasons_of_data": seasons_played,
            "method": "weighted_avg",
        })

    return _finalise(projections, limit)


def get_schedule_difficulty(
    target_season: int = 2026,
    scoring: str = "ppr",
) -> list[dict]:
    """Calculate schedule difficulty for each team in the target season.

    Uses prior season defensive rankings to rate each team's upcoming
    schedule by position.
    """
    ppr_value = {"standard": 0.0, "half_ppr": 0.5, "ppr": 1.0}.get(scoring, 1.0)
    prior_season = target_season - 1

    # Get defensive rankings from prior season
    def_rankings = execute_query("""
        SELECT
            f.opponent_team                             AS defense,
            f.position,
            CAST(AVG(
                COALESCE(f.passing_yards, 0) * 0.04
              + COALESCE(f.passing_tds, 0) * 4.0
              + COALESCE(f.interceptions, 0) * -2.0
              + COALESCE(f.rushing_yards, 0) * 0.1
              + COALESCE(f.rushing_tds, 0) * 6.0
              + COALESCE(f.receptions, 0) * :ppr
              + COALESCE(f.receiving_yards, 0) * 0.1
              + COALESCE(f.receiving_tds, 0) * 6.0
              + COALESCE(f.total_fumbles_lost, 0) * -2.0
            ) AS DECIMAL(10,2))                         AS avg_pts_allowed
        FROM mart.fact_player_week f
        WHERE f.season = :season
          AND f.season_type = 'REG'
          AND f.position IN ('QB', 'RB', 'WR', 'TE')
        GROUP BY f.opponent_team, f.position
    """, {"season": prior_season, "ppr": ppr_value})

    # Build defense lookup: {(defense, position): avg_pts_allowed}
    def_lookup = {}
    pos_averages = {}
    for row in def_rankings:
        key = (row["defense"], row["position"])
        def_lookup[key] = float(row["avg_pts_allowed"])
        pos = row["position"]
        if pos not in pos_averages:
            pos_averages[pos] = []
        pos_averages[pos].append(float(row["avg_pts_allowed"]))

    # Calculate league averages by position
    league_avg = {pos: sum(vals) / len(vals) for pos, vals in pos_averages.items()}

    # Get target season schedule
    schedule = execute_query("""
        SELECT
            game_id,
            season,
            week,
            home_team,
            away_team
        FROM mart.dim_game
        WHERE season = :season
          AND game_type = 'REG'
        ORDER BY week
    """, {"season": target_season})

    if not schedule:
        return []

    # Build team schedules with difficulty ratings
    team_weeks = {}
    for game in schedule:
        week = game["week"]
        home = game["home_team"]
        away = game["away_team"]

        # Home team faces away team's defense
        if home not in team_weeks:
            team_weeks[home] = []
        team_weeks[home].append({
            "week": week,
            "opponent": away,
            "home_away": "home",
        })

        # Away team faces home team's defense
        if away not in team_weeks:
            team_weeks[away] = []
        team_weeks[away].append({
            "week": week,
            "opponent": home,
            "home_away": "away",
        })

    # Calculate schedule difficulty per team per position
    results = []
    for team, weeks in team_weeks.items():
        for pos in ["QB", "RB", "WR", "TE"]:
            week_ratings = []
            for w in weeks:
                opp_defense = w["opponent"]
                pts_allowed = def_lookup.get((opp_defense, pos), league_avg.get(pos, 10))
                avg = league_avg.get(pos, 10)
                # Positive = easy matchup, negative = tough
                difficulty = round(pts_allowed - avg, 1)
                week_ratings.append({
                    "week": w["week"],
                    "opponent": w["opponent"],
                    "home_away": w["home_away"],
                    "opp_pts_allowed": round(pts_allowed, 1),
                    "matchup_rating": difficulty,
                })

            avg_difficulty = sum(w["matchup_rating"] for w in week_ratings) / len(week_ratings) if week_ratings else 0

            results.append({
                "team": team,
                "position": pos,
                "schedule_strength": round(avg_difficulty, 2),
                "total_weeks": len(week_ratings),
                "easy_weeks": sum(1 for w in week_ratings if w["matchup_rating"] > 1),
                "hard_weeks": sum(1 for w in week_ratings if w["matchup_rating"] < -1),
                "weekly_matchups": week_ratings,
            })

    results.sort(key=lambda x: (x["position"], -x["schedule_strength"]))
    return results
