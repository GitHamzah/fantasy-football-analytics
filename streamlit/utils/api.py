"""API client for calling the FastAPI backend."""

import requests
import streamlit as st

try:
    API_BASE = st.secrets["api_url"]
except (FileNotFoundError, KeyError):
    API_BASE = "http://localhost:8000"


def _get(endpoint: str, params: dict = None) -> dict | list | None:
    url = f"{API_BASE}{endpoint}"
    for attempt in range(3):
        try:
            r = requests.get(url, params=params, timeout=60)
            r.raise_for_status()
            return r.json()
        except requests.exceptions.ConnectionError:
            if attempt < 2:
                import time
                time.sleep(2)
                continue
            st.error(f"Could not connect to the API after 3 attempts. URL: {API_BASE}")
            return None
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return None
            st.error(f"API error: {e.response.status_code}")
            return None


def _post(endpoint: str, json_data: dict) -> dict | None:
    try:
        r = requests.post(f"{API_BASE}{endpoint}", json=json_data, timeout=30)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        st.error("Could not connect to the API. Is the FastAPI server running?")
        return None
    except requests.exceptions.HTTPError:
        st.error("Request failed. Check the API logs.")
        return None


# --- Player Dropdown ---
@st.cache_data(ttl=300)
def get_fantasy_players() -> list[dict]:
    """Get all fantasy-relevant players. Cached for 5 minutes."""
    return _get("/players/fantasy-relevant", {"min_season": 2024}) or []


def player_dropdown(label: str, key: str, position_filter: str = None) -> tuple[str, str] | tuple[None, None]:
    """Searchable player dropdown. Returns (player_id, player_name) or (None, None).

    Uses st.selectbox with built-in type-to-search on ~600 players.
    """
    players = get_fantasy_players()
    if not players:
        st.warning("Could not load player list.")
        return None, None

    if position_filter:
        players = [p for p in players if p["position"] == position_filter]

    options = {
        f"{p['player_name']} ({p['position']}, {p.get('current_team') or 'FA'})": p["player_id"]
        for p in players
    }

    # Add empty option at the start
    display_options = [""] + list(options.keys())

    selected = st.selectbox(label, display_options, key=key)

    if not selected:
        return None, None

    player_id = options[selected]
    player_name = selected.split(" (")[0]
    return player_id, player_name


# --- Players ---
def search_players(query: str, position: str = None, limit: int = 20) -> list:
    params = {"q": query, "limit": limit}
    if position:
        params["position"] = position
    return _get("/players/search", params) or []

def get_player(player_id: str) -> dict | None:
    return _get(f"/players/{player_id}")

# --- Stats ---
def get_season_stats(player_id: str, season: int = None, scoring: str = "ppr") -> list:
    params = {"scoring": scoring}
    if season:
        params["season"] = season
    return _get(f"/stats/season/{player_id}", params) or []

def get_weekly_stats(player_id: str, season: int, scoring: str = "ppr") -> list:
    return _get(f"/stats/weekly/{player_id}", {"season": season, "scoring": scoring}) or []

# --- Leaders ---
def get_season_leaders(season: int, position: str = None, scoring: str = "ppr", limit: int = 25) -> list:
    params = {"season": season, "scoring": scoring, "limit": limit}
    if position:
        params["position"] = position
    return _get("/leaders/season", params) or []

def get_weekly_leaders(season: int, week: int, position: str = None, scoring: str = "ppr", limit: int = 25) -> list:
    params = {"season": season, "week": week, "scoring": scoring, "limit": limit}
    if position:
        params["position"] = position
    return _get("/leaders/weekly", params) or []

# --- Analytics ---
def get_consistency(season: int, position: str = None, scoring: str = "ppr", limit: int = 50, min_games: int = 8) -> list:
    params = {"season": season, "scoring": scoring, "limit": limit, "min_games": min_games}
    if position:
        params["position"] = position
    return _get("/analytics/consistency", params) or []

def get_vor(season: int, scoring: str = "ppr", limit: int = 75) -> list:
    return _get("/analytics/vor", {"season": season, "scoring": scoring, "limit": limit}) or []

def get_opportunity(season: int, position: str = None, scoring: str = "ppr", limit: int = 75) -> list:
    params = {"season": season, "scoring": scoring, "limit": limit}
    if position:
        params["position"] = position
    return _get("/analytics/opportunity", params) or []

def get_defensive_rankings(season: int, scoring: str = "ppr") -> list:
    return _get("/analytics/defense", {"season": season, "scoring": scoring}) or []

def get_trajectory(player_id: str, scoring: str = "ppr") -> list:
    return _get(f"/analytics/trajectory/{player_id}", {"scoring": scoring}) or []

def compare_players(player_ids: list[str], season: int, scoring: str = "ppr") -> list:
    return _get("/analytics/compare", {"player_ids": ",".join(player_ids), "season": season, "scoring": scoring}) or []

# --- Projections ---
def get_projections(season: int = 2026, position: str = None, scoring: str = "ppr", limit: int = 150) -> list:
    params = {"season": season, "scoring": scoring, "limit": limit}
    if position:
        params["position"] = position
    return _get("/projections/players", params) or []

def get_schedule_strength(season: int = 2026, position: str = None, scoring: str = "ppr") -> list:
    params = {"season": season, "scoring": scoring}
    if position:
        params["position"] = position
    return _get("/projections/schedule", params) or []

def get_team_schedule(team: str, season: int = 2026, position: str = "RB", scoring: str = "ppr") -> dict | None:
    return _get(f"/projections/schedule/{team}", {"season": season, "position": position, "scoring": scoring})

# --- AI ---
def ask_ai(question: str) -> dict | None:
    return _post("/ai/ask", {"question": question})
