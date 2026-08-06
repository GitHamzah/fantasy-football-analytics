"""📊 Dashboard — Season leaders, VOR, and consistency overview."""

import streamlit as st
import pandas as pd
import plotly.express as px
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from utils.api import get_season_leaders, get_vor, get_consistency

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")
st.title("📊 Season Dashboard")

# Sidebar
scoring_map = {"PPR": "ppr", "Half-PPR": "half_ppr", "Standard": "standard"}
scoring_label = st.sidebar.selectbox("Scoring Format", ["PPR", "Half-PPR", "Standard"])
scoring = scoring_map[scoring_label]
season = st.sidebar.selectbox("Season", [2025, 2024, 2023, 2022, 2021])
position = st.sidebar.selectbox("Position", ["All", "QB", "RB", "WR", "TE"])
pos_filter = None if position == "All" else position

tab_leaders, tab_vor, tab_consistency = st.tabs(["🏆 Leaders", "📈 Value Over Replacement", "🎯 Consistency"])

with tab_leaders:
    with st.spinner("Loading leaders..."):
        leaders = get_season_leaders(season, position=pos_filter, scoring=scoring, limit=30)

    if leaders:
        df = pd.DataFrame(leaders)
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Season", season)
        col2.metric("Format", scoring_label)
        col3.metric("Players", len(df))
        col4.metric("Top Scorer", f"{df.iloc[0]['player_name']} ({df.iloc[0]['fantasy_points']})")

        st.markdown("---")
        display_df = df[["rank", "player_name", "position", "team", "games_played", "fantasy_points", "fantasy_ppg"]].copy()
        display_df.columns = ["Rank", "Player", "Pos", "Team", "GP", "Fantasy Pts", "PPG"]
        st.dataframe(display_df.style.format({"Fantasy Pts": "{:.1f}", "PPG": "{:.1f}"}),
                     use_container_width=True, hide_index=True)

        col_left, col_right = st.columns(2)
        with col_left:
            fig = px.bar(df.head(15), x="player_name", y="fantasy_points", color="position",
                         text="fantasy_points", labels={"player_name": "", "fantasy_points": "Fantasy Pts"})
            fig.update_traces(texttemplate="%{text:.1f}", textposition="outside")
            fig.update_layout(xaxis_tickangle=-45, height=500, title="Total Fantasy Points")
            st.plotly_chart(fig, use_container_width=True)
        with col_right:
            fig = px.bar(df.head(15), x="player_name", y="fantasy_ppg", color="position",
                         text="fantasy_ppg", labels={"player_name": "", "fantasy_ppg": "PPG"})
            fig.update_traces(texttemplate="%{text:.1f}", textposition="outside")
            fig.update_layout(xaxis_tickangle=-45, height=500, title="Points Per Game")
            st.plotly_chart(fig, use_container_width=True)

        if position == "All":
            st.markdown("---")
            st.subheader("Top Scorer by Position")
            pos_cols = st.columns(4)
            for i, pos in enumerate(["QB", "RB", "WR", "TE"]):
                pos_df = df[df["position"] == pos]
                if not pos_df.empty:
                    top = pos_df.iloc[0]
                    pos_cols[i].metric(pos, top["player_name"],
                                       f"{top['fantasy_points']:.1f} pts | {top['fantasy_ppg']:.1f} ppg")
    else:
        st.warning("No data available.")

with tab_vor:
    st.markdown("""
    **Value Over Replacement (VOR)** measures how much better a player is than the 
    "replacement level" player at their position. This is the core metric for draft value.
    """)
    with st.spinner("Calculating VOR..."):
        vor_data = get_vor(season, scoring=scoring, limit=75)
    if vor_data:
        vor_df = pd.DataFrame(vor_data)
        st.subheader("Top Value Over Replacement — PPG")
        fig = px.bar(vor_df.head(25), x="player_name", y="vor_ppg", color="position",
                     text="vor_ppg", hover_data={"ppg": ":.1f", "baseline_ppg": ":.1f", "team": True},
                     labels={"player_name": "", "vor_ppg": "VOR PPG"})
        fig.update_traces(texttemplate="%{text:.1f}", textposition="outside")
        fig.update_layout(xaxis_tickangle=-45, height=500)
        st.plotly_chart(fig, use_container_width=True)

        vor_display = vor_df[["player_name", "position", "team", "games_played", "pos_rank", "ppg", "baseline_ppg", "vor_ppg", "vor_total"]].copy()
        vor_display.columns = ["Player", "Pos", "Team", "GP", "Pos Rank", "PPG", "Baseline PPG", "VOR PPG", "VOR Total"]
        st.dataframe(vor_display.style.format({"PPG": "{:.1f}", "Baseline PPG": "{:.1f}",
                     "VOR PPG": "{:+.1f}", "VOR Total": "{:+.1f}"}),
                     use_container_width=True, hide_index=True)

        st.markdown("---")
        st.subheader("Positional Scarcity — VOR Drop-Off")
        fig = px.line(vor_df, x="pos_rank", y="vor_ppg", color="position", hover_name="player_name",
                      labels={"pos_rank": "Position Rank", "vor_ppg": "VOR PPG"})
        fig.add_hline(y=0, line_dash="dash", line_color="red", annotation_text="Replacement Level")
        fig.update_layout(height=450)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No VOR data available.")

with tab_consistency:
    st.markdown("""
    **Consistency Score** = PPG / Standard Deviation. Higher = more predictable.  
    **Boom** = 20+ points. **Bust** = under 8 points.
    """)
    with st.spinner("Loading consistency data..."):
        consistency = get_consistency(season, position=pos_filter, scoring=scoring, limit=50)
    if consistency:
        con_df = pd.DataFrame(consistency)
        st.subheader("Floor vs Ceiling")
        fig = px.scatter(con_df, x="floor", y="ceiling", color="position",
                         size="ppg", hover_name="player_name",
                         hover_data={"ppg": ":.1f", "std_dev": ":.1f", "boom_pct": ":.0f", "bust_pct": ":.0f"},
                         labels={"floor": "Floor (Worst Week)", "ceiling": "Ceiling (Best Week)"})
        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)

        col_left, col_right = st.columns(2)
        with col_left:
            st.subheader("Highest Boom Rate")
            boom = con_df.sort_values("boom_pct", ascending=False).head(15)
            fig = px.bar(boom, x="player_name", y="boom_pct", color="position",
                         text="boom_pct", labels={"player_name": "", "boom_pct": "Boom %"})
            fig.update_traces(texttemplate="%{text:.0f}%", textposition="outside")
            fig.update_layout(xaxis_tickangle=-45, height=450)
            st.plotly_chart(fig, use_container_width=True)
        with col_right:
            st.subheader("Lowest Bust Rate")
            no_bust = con_df.sort_values("bust_pct").head(15)
            fig = px.bar(no_bust, x="player_name", y="bust_pct", color="position",
                         text="bust_pct", labels={"player_name": "", "bust_pct": "Bust %"})
            fig.update_traces(texttemplate="%{text:.0f}%", textposition="outside")
            fig.update_layout(xaxis_tickangle=-45, height=450)
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        st.subheader("Consistency Rankings")
        con_display = con_df[["player_name", "position", "team", "games_played", "ppg", "std_dev", "floor", "ceiling", "boom_pct", "bust_pct", "consistency_score"]].copy()
        con_display.columns = ["Player", "Pos", "Team", "GP", "PPG", "Std Dev", "Floor", "Ceiling", "Boom %", "Bust %", "Consistency"]
        st.dataframe(con_display.style.format({"PPG": "{:.1f}", "Std Dev": "{:.1f}", "Floor": "{:.1f}",
                     "Ceiling": "{:.1f}", "Boom %": "{:.0f}%", "Bust %": "{:.0f}%", "Consistency": "{:.2f}"}),
                     use_container_width=True, hide_index=True)
    else:
        st.warning("No consistency data available.")
