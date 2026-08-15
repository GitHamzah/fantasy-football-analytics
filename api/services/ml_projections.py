"""ML-based fantasy projections.

Trains a GradientBoostingRegressor to predict a player's NEXT-season fantasy
PPG from their current-season production, usage, consistency and age profile.

Two execution contexts are supported:
  * Training — run from the project root via train_model.py, talking to the
    local SQL Server through src.db.
  * Serving — run inside the API, which loads the saved joblib artifacts and
    queries through api.database (which handles the Postgres dialect).

All SQL here is deliberately dialect-neutral: COALESCE rather than ISNULL, no
TOP, and no STDEV/STDDEV — weekly rows are pulled at their natural grain and
aggregated in pandas, which keeps the same code working on SQL Server and
Postgres alike.
"""

from __future__ import annotations

import os
from datetime import date

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_HERE = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(os.path.dirname(_HERE), "models")
MODEL_PATH = os.path.join(MODEL_DIR, "projection_model.joblib")
FEATURES_PATH = os.path.join(MODEL_DIR, "feature_names.joblib")

# Scoring weights (PPR by default)
PPR_VALUE = 1.0

# A player-season needs this many games to be usable
MIN_GAMES = 8

# Positions we project
POSITIONS = ("QB", "RB", "WR", "TE")

# Below this share of rows matched, PFR features are dropped entirely rather
# than fed to the model as mostly-null noise.
PFR_MIN_MATCH_RATE = 0.70


# ---------------------------------------------------------------------------
# Connection handling — works in both the API and standalone training
# ---------------------------------------------------------------------------

def _get_engine():
    """Return a SQLAlchemy engine, whichever context we are running in."""
    try:
        from database import engine  # API context (api/ is on sys.path)
        return engine
    except ImportError:
        from src.db import get_engine  # training context (project root)
        return get_engine()


def _read_sql(query: str, params: dict | None = None) -> pd.DataFrame:
    """Run a query and return a DataFrame, normalising column names to lower.

    Wrapped in text() so named :params bind the same way on either backend.
    pandas mis-handles an empty params dict, so it is omitted when unused.
    """
    from sqlalchemy import text

    engine = _get_engine()
    stmt = text(query)
    if params:
        df = pd.read_sql(stmt, engine, params=params)
    else:
        df = pd.read_sql(stmt, engine)
    df.columns = [c.lower() for c in df.columns]
    return df


# ---------------------------------------------------------------------------
# A) Data preparation
# ---------------------------------------------------------------------------

_WEEKLY_SQL = """
SELECT
    f.gsis_id,
    f.display_name,
    f.position,
    f.recent_team,
    f.season,
    f.week,
    COALESCE(f.passing_yards, 0) * 0.04
      + COALESCE(f.passing_tds, 0) * 4.0
      + COALESCE(f.interceptions, 0) * -2.0
      + COALESCE(f.rushing_yards, 0) * 0.1
      + COALESCE(f.rushing_tds, 0) * 6.0
      + COALESCE(f.receptions, 0) * {ppr}
      + COALESCE(f.receiving_yards, 0) * 0.1
      + COALESCE(f.receiving_tds, 0) * 6.0
      + COALESCE(f.total_fumbles_lost, 0) * -2.0
      + COALESCE(f.total_2pt_conversions, 0) * 2.0
      + COALESCE(f.special_teams_tds, 0) * 6.0     AS fantasy_points,
    COALESCE(f.targets, 0)                          AS targets,
    COALESCE(f.carries, 0)                          AS carries,
    COALESCE(f.receptions, 0)                       AS receptions,
    COALESCE(f.passing_yards, 0)
      + COALESCE(f.rushing_yards, 0)
      + COALESCE(f.receiving_yards, 0)              AS total_yards,
    COALESCE(f.passing_tds, 0)
      + COALESCE(f.rushing_tds, 0)
      + COALESCE(f.receiving_tds, 0)                AS total_tds,
    f.target_share,
    f.air_yards_share,
    f.wopr
FROM mart.fact_player_week f
WHERE f.season_type = 'REG'
  AND f.position IN ('QB', 'RB', 'WR', 'TE')
"""

_PLAYER_SQL = """
SELECT gsis_id, birth_date, rookie_year, current_team
FROM mart.dim_player
"""

_PFR_SQL = """
SELECT
    LOWER(pfr_player_name)                AS pfr_name,
    team                                  AS pfr_team,
    season,
    week,
    passing_bad_throw_pct,
    times_pressured_pct,
    rushing_yards_before_contact_avg,
    rushing_broken_tackles,
    receiving_drop_pct
FROM mart.pfr_advstats
"""


def _aggregate_to_player_season(weekly: pd.DataFrame) -> pd.DataFrame:
    """Collapse weekly rows to one row per player-season.

    Consistency metrics (std dev, boom, bust) are computed here rather than in
    SQL so the code stays portable across SQL Server and Postgres.
    """
    weekly = weekly.copy()
    weekly["is_boom"] = (weekly["fantasy_points"] >= 20).astype(float)
    weekly["is_bust"] = (weekly["fantasy_points"] < 8).astype(float)

    grouped = weekly.groupby(["gsis_id", "season"], as_index=False).agg(
        display_name=("display_name", "last"),
        position=("position", "last"),
        recent_team=("recent_team", "last"),
        games_played=("fantasy_points", "size"),
        ppg=("fantasy_points", "mean"),
        std_dev=("fantasy_points", "std"),
        boom_rate=("is_boom", "mean"),
        bust_rate=("is_bust", "mean"),
        total_yards_pg=("total_yards", "mean"),
        total_tds_pg=("total_tds", "mean"),
        receptions_pg=("receptions", "mean"),
        targets_pg=("targets", "mean"),
        carries_pg=("carries", "mean"),
        target_share=("target_share", "mean"),
        air_yards_share=("air_yards_share", "mean"),
        wopr=("wopr", "mean"),
    )

    grouped["opportunity_pg"] = grouped["targets_pg"] + grouped["carries_pg"]
    # A single-game season has no defined std dev; treat it as zero spread.
    grouped["std_dev"] = grouped["std_dev"].fillna(0.0)
    return grouped


def _attach_pfr(player_season: pd.DataFrame, verbose: bool = True) -> tuple[pd.DataFrame, bool]:
    """Join PFR advanced stats on name+team+season+week, aggregated to season.

    Returns (dataframe, pfr_included). If the weekly match rate falls below
    PFR_MIN_MATCH_RATE the PFR columns are dropped entirely — a mostly-null
    feature is worse than no feature.
    """
    try:
        pfr = _read_sql(_PFR_SQL)
    except Exception as e:
        if verbose:
            print(f"  PFR query failed ({type(e).__name__}: {e}) — skipping PFR features")
        return player_season, False

    if pfr.empty:
        if verbose:
            print("  PFR table empty — skipping PFR features")
        return player_season, False

    # Season-level PFR aggregates per (name, team, season)
    pfr_season = pfr.groupby(["pfr_name", "pfr_team", "season"], as_index=False).agg(
        passing_bad_throw_pct=("passing_bad_throw_pct", "mean"),
        times_pressured_pct=("times_pressured_pct", "mean"),
        rushing_ybc_avg=("rushing_yards_before_contact_avg", "mean"),
        rushing_broken_tackles_pg=("rushing_broken_tackles", "mean"),
        receiving_drop_pct=("receiving_drop_pct", "mean"),
    )

    merged = player_season.copy()
    merged["_nm"] = merged["display_name"].str.lower()

    out = merged.merge(
        pfr_season,
        left_on=["_nm", "recent_team", "season"],
        right_on=["pfr_name", "pfr_team", "season"],
        how="left",
    ).drop(columns=["_nm", "pfr_name", "pfr_team"], errors="ignore")

    match_rate = out["times_pressured_pct"].notna().mean() if len(out) else 0.0
    # times_pressured_pct only exists for passers, so gauge the join on any hit
    any_hit = out[[
        "passing_bad_throw_pct", "times_pressured_pct", "rushing_ybc_avg",
        "rushing_broken_tackles_pg", "receiving_drop_pct",
    ]].notna().any(axis=1)
    overall_rate = any_hit.mean() if len(out) else 0.0

    if verbose:
        print(f"  PFR join: {int(any_hit.sum()):,}/{len(out):,} player-seasons matched "
              f"({overall_rate:.1%})")

    if overall_rate < PFR_MIN_MATCH_RATE:
        if verbose:
            print(f"  match rate below {PFR_MIN_MATCH_RATE:.0%} — dropping PFR features")
        return player_season, False

    return out, True


def prepare_training_data(
    verbose: bool = True,
    min_games: int = MIN_GAMES,
) -> tuple[pd.DataFrame, bool]:
    """Build the player-season table with next-season PPG as the target.

    Returns (dataframe, pfr_included).
    """
    if verbose:
        print("Loading weekly player stats...")
    weekly = _read_sql(_WEEKLY_SQL.format(ppr=PPR_VALUE))
    if verbose:
        print(f"  weekly rows: {len(weekly):,}")

    player_season = _aggregate_to_player_season(weekly)
    if verbose:
        print(f"  player-seasons (all): {len(player_season):,}")

    player_season = player_season[player_season["games_played"] >= min_games].copy()
    if verbose:
        print(f"  player-seasons with >= {min_games} games: {len(player_season):,}")

    # Age and experience from dim_player
    players = _read_sql(_PLAYER_SQL)
    player_season = player_season.merge(players, on="gsis_id", how="left")

    def _age(row):
        bd = row["birth_date"]
        if pd.isna(bd):
            return np.nan
        if isinstance(bd, str):
            try:
                bd = date.fromisoformat(bd)
            except ValueError:
                return np.nan
        # Age as of the September 1 kickoff of that season
        return row["season"] - bd.year

    player_season["age"] = player_season.apply(_age, axis=1)
    player_season["years_in_league"] = player_season["season"] - player_season["rookie_year"]
    if verbose:
        print(f"  age known for {player_season['age'].notna().sum():,}/{len(player_season):,}")

    # Prior-season PPG (0 when the player has no prior season on file)
    prior = player_season[["gsis_id", "season", "ppg"]].copy()
    prior["season"] = prior["season"] + 1
    prior = prior.rename(columns={"ppg": "ppg_prior"})
    player_season = player_season.merge(prior, on=["gsis_id", "season"], how="left")
    player_season["ppg_prior"] = player_season["ppg_prior"].fillna(0.0)

    # TARGET: next season's PPG
    nxt = player_season[["gsis_id", "season", "ppg"]].copy()
    nxt["season"] = nxt["season"] - 1
    nxt = nxt.rename(columns={"ppg": "target_next_ppg"})
    player_season = player_season.merge(nxt, on=["gsis_id", "season"], how="left")
    if verbose:
        labelled = player_season["target_next_ppg"].notna().sum()
        print(f"  player-seasons with a next-season target: {labelled:,}")

    # PFR advanced features
    player_season, pfr_included = _attach_pfr(player_season, verbose=verbose)

    return player_season, pfr_included


# ---------------------------------------------------------------------------
# B/C) Feature engineering
# ---------------------------------------------------------------------------

BASE_FEATURES = [
    "ppg",
    "ppg_prior",
    "games_played",
    "age",
    "is_qb",
    "is_rb",
    "is_wr",
    "is_te",
    "opportunity_pg",
    "targets_pg",
    "carries_pg",
    "target_share",
    "receptions_pg",
    "total_tds_pg",
    "total_yards_pg",
    "air_yards_share",
    "wopr",
    "std_dev",
    "boom_rate",
    "bust_rate",
    "years_in_league",
]

PFR_FEATURES = [
    "passing_bad_throw_pct",
    "times_pressured_pct",
    "rushing_ybc_avg",
    "rushing_broken_tackles_pg",
    "receiving_drop_pct",
]


def build_features(df: pd.DataFrame, pfr_included: bool) -> tuple[pd.DataFrame, list[str]]:
    """Return (feature_matrix, feature_names) for the given player-seasons."""
    out = df.copy()

    for pos in POSITIONS:
        out[f"is_{pos.lower()}"] = (out["position"] == pos).astype(int)

    feature_names = list(BASE_FEATURES)
    if pfr_included:
        feature_names += PFR_FEATURES

    for col in feature_names:
        if col not in out.columns:
            out[col] = np.nan
        out[col] = pd.to_numeric(out[col], errors="coerce")

    # Age is the only base feature where a missing value is genuinely unknown
    # rather than a true zero; fill it with the positional median.
    if out["age"].isna().any():
        out["age"] = out.groupby("position")["age"].transform(lambda s: s.fillna(s.median()))
    out["age"] = out["age"].fillna(out["age"].median())

    # PFR columns are absent for players the feed does not cover (e.g. a WR has
    # no bad-throw rate). Zero is the correct reading of "did not do this".
    out[feature_names] = out[feature_names].fillna(0.0)

    return out[feature_names], feature_names


# ---------------------------------------------------------------------------
# D) Training
# ---------------------------------------------------------------------------

def train_model(
    train_seasons: tuple[int, ...] = (2021, 2022, 2023),
    validation_season: int = 2024,
    verbose: bool = True,
) -> dict:
    """Train the projection model and persist it to api/models/.

    Trains on `train_seasons` (each predicting its following season) and
    validates on `validation_season` predicting the season after it.
    """
    from sklearn.ensemble import GradientBoostingRegressor
    from sklearn.metrics import mean_absolute_error, r2_score
    import joblib

    df, pfr_included = prepare_training_data(verbose=verbose)

    labelled = df[df["target_next_ppg"].notna()].copy()
    if verbose:
        print(f"\nLabelled player-seasons: {len(labelled):,}")

    train_df = labelled[labelled["season"].isin(train_seasons)].copy()
    valid_df = labelled[labelled["season"] == validation_season].copy()

    if verbose:
        print(f"  train ({'/'.join(map(str, train_seasons))} -> next): {len(train_df):,}")
        print(f"  valid ({validation_season} -> {validation_season + 1}): {len(valid_df):,}")

    if train_df.empty or valid_df.empty:
        raise ValueError(
            f"Not enough labelled data: train={len(train_df)}, valid={len(valid_df)}"
        )

    X_train, feature_names = build_features(train_df, pfr_included)
    y_train = train_df["target_next_ppg"].astype(float)
    X_valid, _ = build_features(valid_df, pfr_included)
    y_valid = valid_df["target_next_ppg"].astype(float)

    if verbose:
        print(f"\nFeature matrix: train {X_train.shape}, valid {X_valid.shape}")
        print(f"Features ({len(feature_names)}): {', '.join(feature_names)}")

    model = GradientBoostingRegressor(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.1,
        min_samples_leaf=10,
        random_state=42,
    )
    model.fit(X_train, y_train)

    preds = model.predict(X_valid)
    mae = float(mean_absolute_error(y_valid, preds))
    r2 = float(r2_score(y_valid, preds))

    # Baseline: naive "next season = this season" carry-forward
    baseline_mae = float(mean_absolute_error(y_valid, valid_df["ppg"].astype(float)))

    importances = sorted(
        zip(feature_names, model.feature_importances_),
        key=lambda kv: kv[1],
        reverse=True,
    )

    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    joblib.dump(feature_names, FEATURES_PATH)
    if verbose:
        print(f"\nSaved model    -> {MODEL_PATH}")
        print(f"Saved features -> {FEATURES_PATH}")

    return {
        "mae": mae,
        "r2": r2,
        "baseline_mae": baseline_mae,
        "n_train": len(train_df),
        "n_valid": len(valid_df),
        "n_features": len(feature_names),
        "feature_names": feature_names,
        "feature_importance": importances,
        "pfr_included": pfr_included,
        "train_seasons": list(train_seasons),
        "validation_season": validation_season,
    }


# ---------------------------------------------------------------------------
# E) Prediction
# ---------------------------------------------------------------------------

def model_exists() -> bool:
    """True when a trained model and its feature list are both on disk."""
    return os.path.exists(MODEL_PATH) and os.path.exists(FEATURES_PATH)


def load_model():
    """Load the persisted model and feature names."""
    import joblib
    return joblib.load(MODEL_PATH), joblib.load(FEATURES_PATH)


def predict_next_season(
    target_season: int = 2026,
    limit: int = 150,
    min_games: int = MIN_GAMES,
    verbose: bool = False,
) -> list[dict]:
    """Predict `target_season` PPG from the prior season's production.

    Games played reuse the existing engine's rule: a player's average
    availability across their seasons on file, capped at 17.
    """
    if not model_exists():
        raise FileNotFoundError(
            f"No trained model at {MODEL_PATH}. Run train_model.py first."
        )

    model, feature_names = load_model()
    source_season = target_season - 1

    df, pfr_included = prepare_training_data(verbose=verbose, min_games=min_games)

    # Availability across every season on file, for the games projection
    availability = (
        df.groupby("gsis_id")["games_played"].mean().rename("avg_games").reset_index()
    )

    current = df[df["season"] == source_season].copy()
    if current.empty:
        return []

    current = current.merge(availability, on="gsis_id", how="left")

    # If the model was trained with PFR features but this frame lacks them
    # (or vice versa), build_features backfills the missing columns with zeros.
    X, _ = build_features(current, pfr_included)
    X = X.reindex(columns=feature_names, fill_value=0.0)

    current["predicted_ppg"] = model.predict(X)

    results = []
    for _, r in current.iterrows():
        projected_games = int(min(17, round(float(r["avg_games"]))))
        predicted_ppg = round(float(r["predicted_ppg"]), 1)
        results.append({
            "player_id": r["gsis_id"],
            "player_name": r["display_name"],
            "position": r["position"],
            "team": r.get("current_team") or r["recent_team"],
            "age": int(r["age"]) + 1 if pd.notna(r["age"]) else None,
            "predicted_ppg": predicted_ppg,
            "predicted_games": projected_games,
            "predicted_total": round(predicted_ppg * projected_games, 1),
            "last_season_ppg": round(float(r["ppg"]), 1),
            "last_season_games": int(r["games_played"]),
        })

    results.sort(key=lambda x: x["predicted_total"], reverse=True)
    return results[:limit]
