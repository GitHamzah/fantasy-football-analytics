"""AI service — retrieves relevant data, sends to Google Gemini, returns answer."""

import re
import httpx
from database import execute_query
from config import get_settings
from models import AIResponse


SYSTEM_PROMPT = """You are a fantasy football analytics assistant. You answer questions 
about NFL player statistics, fantasy football rankings, draft strategy, and waiver wire 
decisions using real data provided to you.

Rules:
- Only use the data provided in the context. Do not make up statistics.
- If the data doesn't contain enough information to answer, say so.
- Be concise and direct. Fantasy managers want quick, actionable answers.
- When comparing players, use specific numbers from the data.
- Default scoring format is Half-PPR unless the user specifies otherwise.
- Reference the seasons and weeks available in the data.
"""


def _detect_season(question: str) -> str:
    """Detect a year in the question and return a SQL filter.

    If the question contains a year like 2024, returns 'f.season = 2024'.
    Otherwise defaults to the latest season in the database.
    """
    year_match = re.search(r'20[12]\d', question)
    if year_match:
        return f"f.season = {int(year_match.group())}"
    return "f.season = (SELECT MAX(season) FROM mart.fact_player_week)"


def _get_relevant_data(question: str) -> str:
    """Pull relevant data based on keywords in the question.

    Detects the target season from the question and uses it
    across all queries for consistent context.
    """
    question_lower = question.lower()
    context_parts = []
    season_filter = _detect_season(question)

    # Pull top season leaders
    try:
        leaders = execute_query(f"""
            SELECT TOP 20
                f.display_name,
                f.position,
                f.recent_team,
                f.season,
                COUNT(*)                    AS games,
                CAST(SUM(
                    ISNULL(f.passing_yards, 0) * 0.04
                  + ISNULL(f.passing_tds, 0) * 4.0
                  + ISNULL(f.interceptions, 0) * -2.0
                  + ISNULL(f.rushing_yards, 0) * 0.1
                  + ISNULL(f.rushing_tds, 0) * 6.0
                  + ISNULL(f.receptions, 0) * 0.5
                  + ISNULL(f.receiving_yards, 0) * 0.1
                  + ISNULL(f.receiving_tds, 0) * 6.0
                  + ISNULL(f.total_fumbles_lost, 0) * -2.0
                  + ISNULL(f.special_teams_tds, 0) * 6.0
                ) AS DECIMAL(10,1))         AS half_ppr_pts,
                CAST(SUM(
                    ISNULL(f.passing_yards, 0) * 0.04
                  + ISNULL(f.passing_tds, 0) * 4.0
                  + ISNULL(f.interceptions, 0) * -2.0
                  + ISNULL(f.rushing_yards, 0) * 0.1
                  + ISNULL(f.rushing_tds, 0) * 6.0
                  + ISNULL(f.receptions, 0) * 0.5
                  + ISNULL(f.receiving_yards, 0) * 0.1
                  + ISNULL(f.receiving_tds, 0) * 6.0
                  + ISNULL(f.total_fumbles_lost, 0) * -2.0
                  + ISNULL(f.special_teams_tds, 0) * 6.0
                ) / NULLIF(COUNT(*), 0) AS DECIMAL(10,1))
                                            AS ppg
            FROM mart.fact_player_week f
            WHERE {season_filter}
              AND f.season_type = 'REG'
            GROUP BY f.display_name, f.position, f.recent_team, f.season
            ORDER BY half_ppr_pts DESC
        """)
        if leaders:
            season = leaders[0]["season"]
            leader_lines = [
                f"  {r['display_name']} ({r['position']}, {r['recent_team']}): "
                f"{r['half_ppr_pts']} pts, {r['ppg']} ppg, {r['games']} games"
                for r in leaders
            ]
            context_parts.append(
                f"Top 20 Half-PPR scorers for {season} regular season:\n"
                + "\n".join(leader_lines)
            )
    except Exception:
        pass

    # If question mentions a player name, try to find their stats
    words = question.split()
    potential_names = [w for w in words if w[0:1].isupper() and len(w) > 2]
    if potential_names:
        name_search = " ".join(potential_names)
        try:
            player_stats = execute_query("""
                SELECT TOP 5
                    f.display_name,
                    f.position,
                    f.recent_team,
                    f.season,
                    f.week,
                    f.opponent_team,
                    ISNULL(f.passing_yards, 0)   AS pass_yds,
                    ISNULL(f.passing_tds, 0)     AS pass_td,
                    ISNULL(f.rushing_yards, 0)   AS rush_yds,
                    ISNULL(f.rushing_tds, 0)     AS rush_td,
                    ISNULL(f.receptions, 0)      AS rec,
                    ISNULL(f.receiving_yards, 0) AS rec_yds,
                    ISNULL(f.receiving_tds, 0)   AS rec_td,
                    ISNULL(f.targets, 0)         AS tgt
                FROM mart.fact_player_week f
                WHERE f.display_name LIKE :name
                ORDER BY f.season DESC, f.week DESC
            """, {"name": f"%{name_search}%"})
            if player_stats:
                name = player_stats[0]["display_name"]
                lines = [
                    f"  Wk{r['week']} {r['season']} vs {r['opponent_team']}: "
                    f"pass {r['pass_yds']}yds/{r['pass_td']}td, "
                    f"rush {r['rush_yds']}yds/{r['rush_td']}td, "
                    f"rec {r['rec']}/{r['tgt']}tgt/{r['rec_yds']}yds/{r['rec_td']}td"
                    for r in player_stats
                ]
                context_parts.append(
                    f"Recent game log for {name} ({player_stats[0]['position']}, {player_stats[0]['recent_team']}):\n"
                    + "\n".join(lines)
                )
        except Exception:
            pass

    # Check for waiver/trending keywords
    if any(kw in question_lower for kw in ["waiver", "pickup", "trending", "breakout", "rising"]):
        try:
            trending = execute_query(f"""
                WITH recent AS (
                    SELECT
                        f.gsis_id,
                        f.display_name,
                        f.position,
                        f.recent_team,
                        f.season,
                        AVG(
                            ISNULL(f.passing_yards, 0) * 0.04
                          + ISNULL(f.passing_tds, 0) * 4.0
                          + ISNULL(f.interceptions, 0) * -2.0
                          + ISNULL(f.rushing_yards, 0) * 0.1
                          + ISNULL(f.rushing_tds, 0) * 6.0
                          + ISNULL(f.receptions, 0) * 0.5
                          + ISNULL(f.receiving_yards, 0) * 0.1
                          + ISNULL(f.receiving_tds, 0) * 6.0
                          + ISNULL(f.total_fumbles_lost, 0) * -2.0
                        ) AS recent_ppg
                    FROM mart.fact_player_week f
                    WHERE {season_filter}
                      AND f.week >= (SELECT MAX(week) - 3 FROM mart.fact_player_week
                                     WHERE {season_filter})
                      AND f.position IN ('QB','RB','WR','TE')
                    GROUP BY f.gsis_id, f.display_name, f.position, f.recent_team, f.season
                ),
                full_season AS (
                    SELECT
                        f.gsis_id,
                        AVG(
                            ISNULL(f.passing_yards, 0) * 0.04
                          + ISNULL(f.passing_tds, 0) * 4.0
                          + ISNULL(f.interceptions, 0) * -2.0
                          + ISNULL(f.rushing_yards, 0) * 0.1
                          + ISNULL(f.rushing_tds, 0) * 6.0
                          + ISNULL(f.receptions, 0) * 0.5
                          + ISNULL(f.receiving_yards, 0) * 0.1
                          + ISNULL(f.receiving_tds, 0) * 6.0
                          + ISNULL(f.total_fumbles_lost, 0) * -2.0
                        ) AS season_ppg
                    FROM mart.fact_player_week f
                    WHERE {season_filter}
                      AND f.position IN ('QB','RB','WR','TE')
                    GROUP BY f.gsis_id
                )
                SELECT TOP 15
                    r.display_name,
                    r.position,
                    r.recent_team,
                    CAST(r.recent_ppg AS DECIMAL(10,1)) AS recent_ppg,
                    CAST(fs.season_ppg AS DECIMAL(10,1)) AS season_ppg,
                    CAST(r.recent_ppg - fs.season_ppg AS DECIMAL(10,1)) AS trend
                FROM recent r
                JOIN full_season fs ON r.gsis_id = fs.gsis_id
                WHERE r.recent_ppg > 10
                ORDER BY (r.recent_ppg - fs.season_ppg) DESC
            """)
            if trending:
                lines = [
                    f"  {r['display_name']} ({r['position']}, {r['recent_team']}): "
                    f"recent {r['recent_ppg']} ppg vs season {r['season_ppg']} ppg "
                    f"(+{r['trend']} trend)"
                    for r in trending
                ]
                context_parts.append(
                    "Trending up (recent 3 weeks vs full season):\n"
                    + "\n".join(lines)
                )
        except Exception:
            pass

    # Available seasons
    try:
        seasons = execute_query("""
            SELECT DISTINCT season FROM mart.fact_player_week ORDER BY season
        """)
        season_list = [str(s["season"]) for s in seasons]
        context_parts.append(f"Available seasons in the database: {', '.join(season_list)}")
    except Exception:
        pass

    return "\n\n".join(context_parts) if context_parts else "No relevant data found."


async def ask_question(question: str) -> AIResponse:
    """Process a natural language question: retrieve data, call Gemini, return answer."""
    settings = get_settings()

    # Get relevant data context
    data_context = _get_relevant_data(question)

    # Build Gemini request
    user_message = (
        f"Here is the relevant data from our fantasy football database:\n\n"
        f"{data_context}\n\n"
        f"Question: {question}"
    )

    payload = {
        "system_instruction": {
            "parts": [{"text": SYSTEM_PROMPT}]
        },
        "contents": [
            {"role": "user", "parts": [{"text": user_message}]}
        ],
        "generationConfig": {
            "maxOutputTokens": 1000,
            "temperature": 0.7,
        },
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{settings.gemini_url}?key={settings.gemini_api_key}",
            headers={"Content-Type": "application/json"},
            json=payload,
        )
        response.raise_for_status()
        result = response.json()

    # Extract text from Gemini response
    answer = result["candidates"][0]["content"]["parts"][0]["text"]

    return AIResponse(
        question=question,
        answer=answer,
        data_context=data_context,
    )