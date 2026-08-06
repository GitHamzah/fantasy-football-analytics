"""🎯 Matchups & Opportunity — Defensive rankings and opportunity analysis."""

import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from utils.api import get_defensive_rankings, get_opportunity

st.set_page_config(page_title="Matchups & Opportunity", page_icon="🎯", layout="wide")
st.title("🎯 Matchups & Opportunity")

scoring_map = {"PPR": "ppr", "Half-PPR": "half_ppr", "Standard": "standard"}
scoring_label = st.sidebar.selectbox("Scoring Format", ["PPR", "Half-PPR", "Standard"])
scoring = scoring_map[scoring_label]
season = st.sidebar.selectbox("Season", [2025, 2024, 2023, 2022, 2021])

tab_matchups, tab_opportunity = st.tabs(["🛡️ Defensive Matchups", "📊 Opportunity vs Production"])

# --- Defensive Matchups ---
with tab_matchups:
    st.markdown("""
    **Which defenses give up the most fantasy points by position?**  
    Use this to evaluate matchups for sit/start decisions and waiver pickups.
    Green = juicy matchup. Red = tough matchup.
    """)

    with st.spinner("Loading defensive rankings..."):
        defense = get_defensive_rankings(season, scoring=scoring)

    if defense:
        def_df = pd.DataFrame(defense)

        pos_tabs = st.tabs(["QB", "RB", "WR", "TE"])
        for pos_tab, pos in zip(pos_tabs, ["QB", "RB", "WR", "TE"]):
            with pos_tab:
                pos_data = def_df[def_df["position"] == pos].sort_values("avg_pts_allowed", ascending=False).copy()
                pos_data["rank"] = range(1, len(pos_data) + 1)

                if pos_data.empty:
                    st.info(f"No defensive data for {pos}.")
                    continue

                # Horizontal bar chart
                fig = px.bar(pos_data, y="defense", x="avg_pts_allowed", orientation="h",
                             color="avg_pts_allowed",
                             color_continuous_scale=["green", "yellow", "red"],
                             text="avg_pts_allowed",
                             labels={"defense": "Defense", "avg_pts_allowed": f"Avg {pos} Fantasy Pts Allowed"},
                             title=f"Fantasy Points Allowed to {pos}s — {season}")
                fig.update_traces(texttemplate="%{text:.1f}", textposition="outside")
                fig.update_layout(height=max(500, len(pos_data) * 22), yaxis=dict(autorange="reversed"),
                                  coloraxis_showscale=False)
                st.plotly_chart(fig, use_container_width=True)

                # Table
                table = pos_data[["rank", "defense", "games", "avg_pts_allowed", "total_pts_allowed"]].copy()
                table.columns = ["Rank", "Defense", "Games", "Avg Pts Allowed", "Total Pts Allowed"]
                st.dataframe(
                    table.style.format({"Avg Pts Allowed": "{:.1f}", "Total Pts Allowed": "{:.1f}"}),
                    use_container_width=True, hide_index=True,
                )
    else:
        st.warning("No defensive data available.")

# --- Opportunity vs Production ---
with tab_opportunity:
    st.markdown("""
    **Are players earning their fantasy points, or are they over/underperforming their usage?**  
    - Players **above** the trendline are efficient — producing more than expected from their opportunity.  
    - Players **below** the trendline with high opportunity are **buy-low candidates** — due for positive regression.  
    - Players **above** with low opportunity are **sell-high candidates** — efficiency likely to regress.
    """)

    opp_position = st.selectbox("Position Filter", ["All Skill", "RB", "WR", "TE"], key="opp_pos")
    opp_pos = None if opp_position == "All Skill" else opp_position

    with st.spinner("Loading opportunity data..."):
        opp_data = get_opportunity(season, position=opp_pos, scoring=scoring, limit=75)

    if opp_data:
        opp_df = pd.DataFrame(opp_data)

        # Main scatter: Opportunity vs PPG
        fig = px.scatter(opp_df, x="opportunities_pg", y="fantasy_ppg",
                         color="position", size="games_played",
                         hover_name="player_name",
                         hover_data={
                             "team": True, "targets_pg": ":.1f", "carries_pg": ":.1f",
                             "target_share_pct": ":.1f", "fantasy_ppg": ":.1f",
                             "opportunities_pg": ":.1f",
                         },
                         labels={
                             "opportunities_pg": "Opportunities per Game (Targets + Carries)",
                             "fantasy_ppg": "Fantasy PPG",
                         },
                         title=f"Opportunity vs Fantasy Production — {season} ({scoring_label})")

        # Add trendline
        if len(opp_df) > 2:
            z = np.polyfit(opp_df["opportunities_pg"], opp_df["fantasy_ppg"], 1)
            x_range = [opp_df["opportunities_pg"].min(), opp_df["opportunities_pg"].max()]
            fig.add_scatter(x=x_range, y=[z[0]*x + z[1] for x in x_range],
                            mode="lines", name="Trendline",
                            line=dict(dash="dash", color="rgba(255,255,255,0.4)"))

        fig.update_layout(height=550)
        st.plotly_chart(fig, use_container_width=True)

        # Target share scatter
        st.markdown("---")
        st.subheader("Target Share vs Fantasy PPG")
        ts_df = opp_df[opp_df["target_share_pct"] > 0]
        if not ts_df.empty:
            fig2 = px.scatter(ts_df, x="target_share_pct", y="fantasy_ppg",
                              color="position", hover_name="player_name",
                              hover_data={"team": True, "targets_pg": ":.1f", "wopr": ":.3f"},
                              labels={"target_share_pct": "Target Share %", "fantasy_ppg": "Fantasy PPG"},
                              title="Target Share vs Production — High share + low PPG = buy candidate")
            fig2.update_layout(height=450)
            st.plotly_chart(fig2, use_container_width=True)

        # Table
        st.markdown("---")
        opp_display = opp_df[["player_name", "position", "team", "games_played", "opportunities_pg",
                               "targets_pg", "carries_pg", "target_share_pct", "wopr", "fantasy_ppg"]].copy()
        opp_display.columns = ["Player", "Pos", "Team", "GP", "Opps/G", "Tgt/G", "Car/G", "Tgt Share %", "WOPR", "PPG"]
        st.dataframe(
            opp_display.style.format({
                "Opps/G": "{:.1f}", "Tgt/G": "{:.1f}", "Car/G": "{:.1f}",
                "Tgt Share %": "{:.1f}", "WOPR": "{:.3f}", "PPG": "{:.1f}",
            }),
            use_container_width=True, hide_index=True,
        )
    else:
        st.warning("No opportunity data available.")
