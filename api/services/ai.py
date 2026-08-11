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


def _detect_position(question: str) -> str | None:
    """Detect a fantasy position from the question text."""
    q = question.lower()
    position_map = {
        "quarterback": "QB", "qb": "QB",
        "running back": "RB", "rb": "RB", "rusher": "RB",
        "wide receiver": "WR", "wr": "WR", "receiver": "WR", "wideout": "WR",
        "tight end": "TE", "te": "TE",
        "kicker": "K", "k": "K",
        "defense": "DEF", "dst": "DEF",
    }
    # Whole-word matches only, longest phrase first. Without word boundaries
    # short aliases match inside ordinary words ("te" in "consistent"), and
    # without the length ordering "te" would beat "kicker" and "tight end".
    for phrase in sorted(position_map, key=len, reverse=True):
        if re.search(rf"\b{re.escape(phrase)}\b", q):
            return position_map[phrase]
    return None


# Capitalized words that start questions or act as superlatives — never player names.
NON_NAME_WORDS = {
    "Who", "What", "When", "Where", "Which", "How", "Any", "The", "Can",
    "Does", "Did", "Should", "Would", "Could", "Is", "Are", "Was", "Were",
    "Will", "Best", "Top", "Most", "Compare",
}


def _detect_player_name(question: str) -> str | None:
    """Find a likely player name: 2+ consecutive capitalized words.

    Requires a first+last name pattern like "Josh Allen" so that a single
    capitalized word ("Any", "Who") cannot trigger a bogus player lookup.
    """
    # Keep periods, apostrophes and hyphens so "T.J.", "Ja'Marr" and
    # "Amon-Ra" survive tokenization as single words.
    tokens = re.findall(r"[A-Za-z][A-Za-z.'\-]*", question)

    best: list[str] = []
    run: list[str] = []
    for token in tokens:
        if len(token) > 1 and token[0].isupper() and token not in NON_NAME_WORDS:
            run.append(token)
            if len(run) > len(best):
                best = list(run)
        else:
            run = []

    return " ".join(best) if len(best) >= 2 else None


def _get_relevant_data(question: str) -> str:
    """Pull relevant data based on keywords in the question.

    Detects the target season from the question and uses it
    across all queries for consistent context.
    """
    question_lower = question.lower()
    context_parts = []
    season_filter = _detect_season(question)
    position = _detect_position(question)
    position_filter = f"\n              AND f.position = '{position}'" if position else ""

    # Pull top season leaders
    try:
        leaders = execute_query(f"""
            SELECT
                f.display_name,
                f.position,
                f.recent_team,
                f.season,
                COUNT(*)                    AS games,
                CAST(SUM(
                    COALESCE(f.passing_yards, 0) * 0.04
                  + COALESCE(f.passing_tds, 0) * 4.0
                  + COALESCE(f.interceptions, 0) * -2.0
                  + COALESCE(f.rushing_yards, 0) * 0.1
                  + COALESCE(f.rushing_tds, 0) * 6.0
                  + COALESCE(f.receptions, 0) * 0.5
                  + COALESCE(f.receiving_yards, 0) * 0.1
                  + COALESCE(f.receiving_tds, 0) * 6.0
                  + COALESCE(f.total_fumbles_lost, 0) * -2.0
                  + COALESCE(f.special_teams_tds, 0) * 6.0
                ) AS DECIMAL(10,1))         AS half_ppr_pts,
                CAST(SUM(
                    COALESCE(f.passing_yards, 0) * 0.04
                  + COALESCE(f.passing_tds, 0) * 4.0
                  + COALESCE(f.interceptions, 0) * -2.0
                  + COALESCE(f.rushing_yards, 0) * 0.1
                  + COALESCE(f.rushing_tds, 0) * 6.0
                  + COALESCE(f.receptions, 0) * 0.5
                  + COALESCE(f.receiving_yards, 0) * 0.1
                  + COALESCE(f.receiving_tds, 0) * 6.0
                  + COALESCE(f.total_fumbles_lost, 0) * -2.0
                  + COALESCE(f.special_teams_tds, 0) * 6.0
                ) / NULLIF(COUNT(*), 0) AS DECIMAL(10,1))
                                            AS ppg
            FROM mart.fact_player_week f
            WHERE {season_filter}
              AND f.season_type = 'REG'{position_filter}
            GROUP BY f.display_name, f.position, f.recent_team, f.season
            ORDER BY half_ppr_pts DESC
            OFFSET 0 ROWS FETCH NEXT 20 ROWS ONLY
        """)
        if leaders:
            season = leaders[0]["season"]
            leader_lines = [
                f"  {r['display_name']} ({r['position']}, {r['recent_team']}): "
                f"{r['half_ppr_pts']} pts, {r['ppg']} ppg, {r['games']} games"
                for r in leaders
            ]
            scope = f"{position} " if position else ""
            context_parts.append(
                f"Top 20 {scope}Half-PPR scorers for {season} regular season:\n"
                + "\n".join(leader_lines)
            )
    except Exception as e:
        import traceback
        print(f"AI data retrieval error: {e}")
        traceback.print_exc()

    # If question mentions a player name, try to find their stats
    name_search = _detect_player_name(question)
    if name_search:
        try:
            player_stats = execute_query("""
                SELECT
                    f.display_name,
                    f.position,
                    f.recent_team,
                    f.season,
                    f.week,
                    f.opponent_team,
                    COALESCE(f.passing_yards, 0)   AS pass_yds,
                    COALESCE(f.passing_tds, 0)     AS pass_td,
                    COALESCE(f.rushing_yards, 0)   AS rush_yds,
                    COALESCE(f.rushing_tds, 0)     AS rush_td,
                    COALESCE(f.receptions, 0)      AS rec,
                    COALESCE(f.receiving_yards, 0) AS rec_yds,
                    COALESCE(f.receiving_tds, 0)   AS rec_td,
                    COALESCE(f.targets, 0)         AS tgt
                FROM mart.fact_player_week f
                WHERE f.display_name LIKE :name
                ORDER BY f.season DESC, f.week DESC
                OFFSET 0 ROWS FETCH NEXT 5 ROWS ONLY
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
        except Exception as e:
            import traceback
            print(f"AI data retrieval error: {e}")
            traceback.print_exc()

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
                            COALESCE(f.passing_yards, 0) * 0.04
                          + COALESCE(f.passing_tds, 0) * 4.0
                          + COALESCE(f.interceptions, 0) * -2.0
                          + COALESCE(f.rushing_yards, 0) * 0.1
                          + COALESCE(f.rushing_tds, 0) * 6.0
                          + COALESCE(f.receptions, 0) * 0.5
                          + COALESCE(f.receiving_yards, 0) * 0.1
                          + COALESCE(f.receiving_tds, 0) * 6.0
                          + COALESCE(f.total_fumbles_lost, 0) * -2.0
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
                            COALESCE(f.passing_yards, 0) * 0.04
                          + COALESCE(f.passing_tds, 0) * 4.0
                          + COALESCE(f.interceptions, 0) * -2.0
                          + COALESCE(f.rushing_yards, 0) * 0.1
                          + COALESCE(f.rushing_tds, 0) * 6.0
                          + COALESCE(f.receptions, 0) * 0.5
                          + COALESCE(f.receiving_yards, 0) * 0.1
                          + COALESCE(f.receiving_tds, 0) * 6.0
                          + COALESCE(f.total_fumbles_lost, 0) * -2.0
                        ) AS season_ppg
                    FROM mart.fact_player_week f
                    WHERE {season_filter}
                      AND f.position IN ('QB','RB','WR','TE')
                    GROUP BY f.gsis_id
                )
                SELECT
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
                OFFSET 0 ROWS FETCH NEXT 15 ROWS ONLY
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
        except Exception as e:
            import traceback
            print(f"AI data retrieval error: {e}")
            traceback.print_exc()

    # Available seasons
    try:
        seasons = execute_query("""
            SELECT DISTINCT season FROM mart.fact_player_week ORDER BY season
        """)
        season_list = [str(s["season"]) for s in seasons]
        context_parts.append(f"Available seasons in the database: {', '.join(season_list)}")
    except Exception as e:
        import traceback
        print(f"AI data retrieval error: {e}")
        traceback.print_exc()

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