"""
train_model.py — Train the ML fantasy projection model.

Run from the project root with the venv activated:

    python train_model.py

Trains a GradientBoostingRegressor on 2021-2023 player-seasons (each predicting
the following season's PPG), validates on 2024 -> 2025, and saves the fitted
model to api/models/projection_model.joblib.
"""

import sys
import os

# Only the project root goes on sys.path. Deliberately NOT api/ — with api/ on
# the path the module would resolve its engine through api/database.py, whose
# dev settings point at localhost. From the root it falls through to src.db and
# picks up the real SQL Server from config/config.yaml.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.services.ml_projections import train_model


def main():
    print("=" * 70)
    print("Fantasy Football Analytics — ML Projection Model Training")
    print("=" * 70)
    print()

    result = train_model(verbose=True)

    print()
    print("=" * 70)
    print("VALIDATION METRICS")
    print("=" * 70)
    print(f"  Train seasons      : {result['train_seasons']} (predicting next season)")
    print(f"  Validation season  : {result['validation_season']} "
          f"-> {result['validation_season'] + 1}")
    print(f"  Train samples      : {result['n_train']:,}")
    print(f"  Validation samples : {result['n_valid']:,}")
    print(f"  Features used      : {result['n_features']}")
    print(f"  PFR features       : {'INCLUDED' if result['pfr_included'] else 'SKIPPED'}")
    print()
    print(f"  MAE                : {result['mae']:.3f} fantasy points per game")
    print(f"  R²                 : {result['r2']:.4f}")
    print(f"  Baseline MAE       : {result['baseline_mae']:.3f} "
          f"(naive carry-forward of this season's PPG)")

    improvement = result["baseline_mae"] - result["mae"]
    pct = (improvement / result["baseline_mae"] * 100) if result["baseline_mae"] else 0
    print(f"  Improvement        : {improvement:+.3f} MAE ({pct:+.1f}% vs baseline)")

    print()
    print("=" * 70)
    print("TOP 20 FEATURE IMPORTANCES")
    print("=" * 70)
    for i, (name, importance) in enumerate(result["feature_importance"][:20], 1):
        bar = "#" * int(round(importance * 60))
        print(f"  {i:2}. {name:32} {importance:7.4f}  {bar}")

    print()
    print("Training complete.")


if __name__ == "__main__":
    main()
