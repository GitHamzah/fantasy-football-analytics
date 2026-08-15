"""Projection endpoints — fantasy projections for upcoming season."""

from fastapi import APIRouter, Query
from services.projections import get_player_projections, get_schedule_difficulty

router = APIRouter(prefix="/projections", tags=["Projections"])


@router.get("/players")
def get_projections(
    season: int = Query(2026, description="Target season to project"),
    position: str | None = Query(None, description="Filter by position"),
    scoring: str = Query("ppr", description="standard, half_ppr, ppr"),
    limit: int = Query(150, ge=1, le=300),
    min_games: int = Query(6, description="Minimum games in a season to qualify"),
):
    """Projected fantasy rankings for the target season.

    Uses a trained gradient boosting model when one is available (PPR scoring
    only), otherwise weighted historical averages with age curve adjustments.
    Each row's `method` field reports which was used: "ml" or "weighted_avg".
    """
    # Pull a wide pool first. Applying the caller's limit here would truncate
    # before the position filter runs, so ?position=RB&limit=5 would come back
    # empty whenever the top 5 overall happen to be QBs.
    projections = get_player_projections(
        target_season=season, scoring=scoring, min_games=min_games, limit=500,
    )

    if position:
        projections = [p for p in projections if p["position"] == position.upper()]
        # Re-rank within position
        for i, p in enumerate(projections, 1):
            p["pos_rank"] = i

    return projections[:limit]


@router.get("/schedule")
def get_schedule_strength(
    season: int = Query(2026, description="Target season"),
    position: str | None = Query(None, description="Filter by position"),
    scoring: str = Query("ppr", description="standard, half_ppr, ppr"),
):
    """Schedule difficulty ratings by team and position for the target season.

    Based on prior season defensive rankings. Positive = easy matchups,
    negative = tough matchups.
    """
    data = get_schedule_difficulty(target_season=season, scoring=scoring)

    if position:
        data = [d for d in data if d["position"] == position.upper()]

    return data


@router.get("/schedule/{team}")
def get_team_schedule(
    team: str,
    season: int = Query(2026, description="Target season"),
    position: str = Query("RB", description="Position for matchup ratings"),
    scoring: str = Query("ppr", description="standard, half_ppr, ppr"),
):
    """Week-by-week schedule with matchup difficulty for a specific team and position."""
    data = get_schedule_difficulty(target_season=season, scoring=scoring)

    for entry in data:
        if entry["team"] == team.upper() and entry["position"] == position.upper():
            return entry

    return {"error": f"No schedule found for {team.upper()} {position.upper()} in {season}"}
