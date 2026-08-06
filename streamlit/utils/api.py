"""API client for calling the FastAPI backend."""

import requests
import streamlit as st

try:
    API_BASE = st.secrets["api_url"]
except (FileNotFoundError, KeyError):
    API_BASE = "http://localhost:8000"


def _get(endpoint: str, params: dict = None) -> dict | list | None:
    try:
        r = requests.get(f"{API_BASE}{endpoint}", params=params, timeout=15)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        st.error("Could not connect to the API. Is the FastAPI server running?")
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


# --- Players ---
def search_players(query: str, position: str = None, limit: int = 20) -> list:
    params = {"q": query, "limit": limit}
    if position:
        params["position"] = position
    return _get("/players/search", params) or []


def get_player(player_id: str) -> dict | None:
    return _get(f"/players/{player_id}")


# --- Stats ---
def get_season_stats(player_id: str, season: int = None, scoring: str = "half_ppr") -> list:
    params = {"scoring": scoring}
    if season:
        params["season"] = season
    return _get(f"/stats/season/{player_id}", params) or []


def get_weekly_stats(player_id: str, season: int, scoring: str = "half_ppr") -> list:
    params = {"season": season, "scoring": scoring}
    return _get(f"/stats/weekly/{player_id}", params) or []


# --- Leaders ---
def get_season_leaders(season: int, position: str = None, scoring: str = "half_ppr", limit: int = 25) -> list:
    params = {"season": season, "scoring": scoring, "limit": limit}
    if position:
        params["position"] = position
    return _get("/leaders/season", params) or []


def get_weekly_leaders(season: int, week: int, position: str = None, scoring: str = "half_ppr", limit: int = 25) -> list:
    params = {"season": season, "week": week, "scoring": scoring, "limit": limit}
    if position:
        params["position"] = position
    return _get("/leaders/weekly", params) or []


# --- Analytics ---
def get_consistency(season: int, position: str = None, scoring: str = "half_ppr", limit: int = 50, min_games: int = 8) -> list:
    params = {"season": season, "scoring": scoring, "limit": limit, "min_games": min_games}
    if position:
        params["position"] = position
    return _get("/analytics/consistency", params) or []


def get_vor(season: int, scoring: str = "half_ppr", limit: int = 75) -> list:
    params = {"season": season, "scoring": scoring, "limit": limit}
    return _get("/analytics/vor", params) or []


def get_opportunity(season: int, position: str = None, scoring: str = "half_ppr", limit: int = 75) -> list:
    params = {"season": season, "scoring": scoring, "limit": limit}
    if position:
        params["position"] = position
    return _get("/analytics/opportunity", params) or []


def get_defensive_rankings(season: int, scoring: str = "half_ppr") -> list:
    params = {"season": season, "scoring": scoring}
    return _get("/analytics/defense", params) or []


def get_trajectory(player_id: str, scoring: str = "half_ppr") -> list:
    params = {"scoring": scoring}
    return _get(f"/analytics/trajectory/{player_id}", params) or []


def compare_players(player_ids: list[str], season: int, scoring: str = "half_ppr") -> list:
    params = {"player_ids": ",".join(player_ids), "season": season, "scoring": scoring}
    return _get("/analytics/compare", params) or []


# --- AI ---
def ask_ai(question: str) -> dict | None:
    return _post("/ai/ask", {"question": question})
