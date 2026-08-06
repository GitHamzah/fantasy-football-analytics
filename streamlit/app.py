"""Fantasy Football Analytics — Home Page."""

import streamlit as st

st.set_page_config(
    page_title="Fantasy Football Analytics",
    page_icon="🏈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🏈 Fantasy Football Analytics")
st.markdown("---")

st.markdown("""
**Free fantasy football analytics powered by real NFL data.**

This platform provides season and weekly stats, fantasy scoring across 
Standard, Half-PPR, and PPR formats, draft prep tools, and an AI assistant 
that answers questions about player performance — all backed by data from 
the [nflverse](https://github.com/nflverse) ecosystem.

### Pages

- **📊 Dashboard** — Season leaders, position breakdowns, and scoring format comparison
- **🔍 Player Lookup** — Search any player, view their stats and weekly trends
- **📋 Draft Board** — Ranked players across seasons for draft preparation
- **🤖 AI Assistant** — Ask natural language questions about fantasy football data

### Data Coverage

- **Seasons:** 2021 – 2025
- **Scoring Formats:** Standard, Half-PPR, PPR
- **Stats:** Passing, rushing, receiving, targets, air yards, EPA, and more
- **Updated:** Weekly during the NFL season via nflverse

---

*Built with Python, FastAPI, dbt, SQL Server, and Streamlit.*
""")

st.sidebar.markdown("### Scoring Format")
st.sidebar.selectbox(
    "Default format",
    ["Half-PPR", "Standard", "PPR"],
    key="global_scoring",
    help="Used across all pages unless overridden.",
)
