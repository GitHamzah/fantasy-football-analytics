"""Fantasy Football Analytics — home / navigation hub."""

import streamlit as st

from utils.components import (
    inject_custom_css,
    render,
    section_header,
    sidebar,
    SCORING_LABELS,
)

st.set_page_config(
    page_title="Fantasy Football Analytics",
    page_icon="🏈",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_custom_css()
scoring, _ = sidebar(show_season=False)


# --- Hero ---------------------------------------------------------------

render("""
    <div style="margin-bottom:6px">
        <span style="font-size:2.1rem;font-weight:800;color:#f1f5f9">
            Fantasy Football Analytics
        </span>
    </div>
    <div style="color:#94a3b8;font-size:1rem;max-width:760px;line-height:1.6;
                margin-bottom:28px">
        Draft, start/sit and waiver decisions built on five seasons of nflverse
        data and Pro Football Reference advanced stats — with next-season
        projections from a trained gradient boosting model.
    </div>
""")


# --- Navigation cards ---------------------------------------------------

section_header("Where do you want to start?")

PAGES = [
    {
        "title": "🏆 Draft War Room",
        "question": "Who should I draft?",
        "body": (
            "2026 projections with position scarcity curves, tiered rankings by "
            "position, and a full draft card for any player — trajectory, "
            "schedule difficulty and advanced metrics in one view."
        ),
    },
    {
        "title": "⚖️ Start / Sit Advisor",
        "question": "Who do I start this week?",
        "body": (
            "A defense heat map showing which positions to attack against which "
            "teams, head-to-head comparison with floor/ceiling and boom/bust "
            "rates, plus a clear verdict — and DST rankings for streaming."
        ),
    },
    {
        "title": "📈 Waiver Wire",
        "question": "Who should I pick up?",
        "body": (
            "Players whose recent three-week form has outrun their season average, "
            "pickups whose upcoming schedule softens, and defenses worth streaming "
            "based on the offenses they are about to face."
        ),
    },
    {
        "title": "🔍 Player Intel",
        "question": "How good is this player, really?",
        "body": (
            "Everything on one screen: career trajectory, week-by-week scoring with "
            "boom/bust bands, PFR advanced metrics, and a scouting view of the "
            "defense they are about to line up against."
        ),
    },
]

cols = st.columns(2)
for i, page in enumerate(PAGES):
    with cols[i % 2]:
        render(f"""
            <div class="nav-card">
                <div class="nav-card-title">{page['title']}</div>
                <div class="nav-card-q">“{page['question']}”</div>
                <div class="nav-card-body">{page['body']}</div>
            </div>
        """)
        st.write("")

render("""
    <div class="nav-card" style="min-height:0;margin-top:4px">
        <div class="nav-card-title">🤖 AI Analyst</div>
        <div class="nav-card-q">“Just ask me a question.”</div>
        <div class="nav-card-body">
            Ask anything in plain English — the assistant pulls real numbers from
            the warehouse before answering, so the response cites actual data
            rather than guessing.
        </div>
    </div>
""")

st.write("")
st.caption(
    f"Pick a page from the sidebar. Scoring format is set to "
    f"**{SCORING_LABELS[scoring]}** and applies across every page."
)
