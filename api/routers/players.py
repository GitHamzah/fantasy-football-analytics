"""Player lookup and search endpoints."""

from fastapi import APIRouter, Query, HTTPException
from database import execute_query
from models import PlayerSummary, PlayerDetail

router = APIRouter(prefix="/players", tags=["Players"])


@router.get("/search", response_model=list[PlayerSummary])
def search_players(
    q: str = Query(..., min_length=2, description="Player name search"),
    position: str | None = Query(None, description="Filter by position (QB, RB, WR, TE)"),
    limit: int = Query(20, ge=1, le=100),
):
    """Search players by name with optional position filter."""
    where = "WHERE display_name LIKE :search"
    params = {"search": f"%{q}%", "limit": limit}

    if position:
        where += " AND position = :position"
        params["position"] = position.upper()

    rows = execute_query(f"""
        SELECT TOP (:limit)
            gsis_id        AS player_id,
            display_name   AS player_name,
            position,
            position_group,
            current_team
        FROM mart.dim_player
        {where}
        ORDER BY display_name
    """, params)

    return rows


@router.get("/{player_id}", response_model=PlayerDetail)
def get_player(player_id: str):
    """Get detailed player info by ID."""
    rows = execute_query("""
        SELECT
            gsis_id        AS player_id,
            display_name   AS player_name,
            position,
            position_group,
            current_team,
            college,
            rookie_year,
            draft_year,
            draft_round,
            draft_pick,
            height_inches,
            weight_lbs,
            status
        FROM mart.dim_player
        WHERE gsis_id = :player_id
    """, {"player_id": player_id})

    if not rows:
        raise HTTPException(status_code=404, detail="Player not found")
    return rows[0]
