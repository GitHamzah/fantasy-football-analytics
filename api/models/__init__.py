"""Pydantic response models for API endpoints."""

from pydantic import BaseModel
from datetime import date


class PlayerSummary(BaseModel):
    player_id: str
    player_name: str | None
    position: str | None
    position_group: str | None
    current_team: str | None


class PlayerDetail(PlayerSummary):
    college: str | None = None
    rookie_year: int | None = None
    draft_year: int | None = None
    draft_round: int | None = None
    draft_pick: int | None = None
    height_inches: int | None = None
    weight_lbs: int | None = None
    status: str | None = None


class PlayerSeasonStats(BaseModel):
    player_id: str
    player_name: str | None
    position: str | None
    team: str | None
    season: int
    games_played: int
    fantasy_points: float
    fantasy_ppg: float
    passing_yards: float
    passing_tds: int
    interceptions: int
    rushing_yards: float
    rushing_tds: int
    receptions: int
    targets: int
    receiving_yards: float
    receiving_tds: int
    total_fumbles_lost: int


class PlayerWeekStats(BaseModel):
    player_id: str
    player_name: str | None
    position: str | None
    team: str | None
    season: int
    week: int
    opponent: str | None
    fantasy_points: float
    passing_yards: float
    passing_tds: int
    interceptions: int
    rushing_yards: float
    rushing_tds: int
    receptions: int
    targets: int
    receiving_yards: float
    receiving_tds: int


class LeaderEntry(BaseModel):
    rank: int
    player_id: str
    player_name: str | None
    position: str | None
    team: str | None
    games_played: int
    fantasy_points: float
    fantasy_ppg: float


class WaiverTarget(BaseModel):
    player_id: str
    player_name: str | None
    position: str | None
    team: str | None
    games_played: int
    fantasy_ppg: float
    recent_fpg: float  # last 3 weeks average
    trend: float  # recent_fpg - season_fpg
    target_share: float | None
    snap_trend: str | None  # placeholder for future snap data


class AIRequest(BaseModel):
    question: str


class AIResponse(BaseModel):
    question: str
    answer: str
    data_context: str | None = None
