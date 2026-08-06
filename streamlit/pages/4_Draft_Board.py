"""📋 Draft Board — VOR-based rankings for draft preparation."""

import streamlit as st
import pandas as pd
import plotly.express as px
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from utils.api import get_vor, get_season_leaders

st.set_page_config(page_title="Draft Board", page_icon="📋", layout="wide")
st.title("📋 Draft Board")

st.markdown("""
Draft rankings based on **Value Over Replacement** — the metric that accounts for positional 
scarcity. A RB with 16 PPG can be more valuable than a QB with 20 PPG if the replacement-level 
RB only scores 8 PPG while the replacement QB scores 15.
""")

scoring_map = {"PPR": "ppr", "Half-PPR": "half_ppr", "Standard": "standard"}
scoring_label = st.sidebar.selectbox("Scoring Format", ["PPR", "Half-PPR", "Standard"])
scoring = scoring_map[scoring_label]
season = st.sidebar.selectbox("Primary Season", [2025, 2024, 2023, 2022, 2021])
compare_season = st.sidebar.selectbox("Compare Season", [None, 2025, 2024, 2023, 2022, 2021])
limit = st.sidebar.slider("Players to Show", 25, 150, 75)

tab_vor, tab_raw, tab_compare = st.tabs(["📈 VOR Rankings", "🏆 Raw Rankings", "🔄 Season Comparison"])

# --- VOR Rankings ---
with tab_vor:
    with st.spinner("Calculating VOR..."):
        vor_data = get_vor(season, scoring=scoring, limit=limit)

    if vor_data:
        vor_df = pd.DataFrame(vor_data)

        # Position tabs within VOR
        pos_tabs = st.tabs(["Overall", "QB", "RB", "WR", "TE"])
        for pos_tab, pos in zip(pos_tabs, ["All", "QB", "RB", "WR", "TE"]):
            with pos_tab:
                if pos == "All":
                    pos_df = vor_df.copy()
                    pos_df["vor_rank"] = range(1, len(pos_df) + 1)
                else:
                    pos_df = vor_df[vor_df["position"] == pos].copy()
                    pos_df["vor_rank"] = range(1, len(pos_df) + 1)

                if pos_df.empty:
                    st.info(f"No {pos} data.")
                    continue

                display = pos_df[["vor_rank", "player_name", "position", "team", "games_played", "ppg", "vor_ppg", "vor_total", "pos_rank"]].copy()
                display.columns = ["VOR Rank", "Player", "Pos", "Team", "GP", "PPG", "VOR PPG", "VOR Total", "Pos Rank"]
                st.dataframe(
                    display.style.format({
                        "PPG": "{:.1f}", "VOR PPG": "{:+.1f}", "VOR Total": "{:+.1f}",
                    }),
                    use_container_width=True, hide_index=True, height=600,
                )

                # VOR bar chart for this position
                chart = pos_df.head(20)
                fig = px.bar(chart, x="player_name", y="vor_ppg", color="position" if pos == "All" else None,
                             text="vor_ppg",
                             labels={"player_name": "", "vor_ppg": "VOR PPG"})
                fig.update_traces(texttemplate="%{text:+.1f}", textposition="outside")
                fig.update_layout(xaxis_tickangle=-45, height=450)
                fig.add_hline(y=0, line_dash="dash", line_color="red")
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No VOR data available.")

# --- Raw Rankings ---
with tab_raw:
    with st.spinner("Loading raw rankings..."):
        leaders = get_season_leaders(season, scoring=scoring, limit=limit)

    if leaders:
        df = pd.DataFrame(leaders)
        pos_tabs = st.tabs(["Overall", "QB", "RB", "WR", "TE"])
        for pos_tab, pos in zip(pos_tabs, ["All", "QB", "RB", "WR", "TE"]):
            with pos_tab:
                if pos == "All":
                    pos_df = df.copy()
                else:
                    pos_df = df[df["position"] == pos].copy()
                    pos_df["rank"] = range(1, len(pos_df) + 1)

                display = pos_df[["rank", "player_name", "position", "team", "games_played", "fantasy_points", "fantasy_ppg"]].copy()
                display.columns = ["Rank", "Player", "Pos", "Team", "GP", "Total Pts", "PPG"]
                st.dataframe(
                    display.style.format({"Total Pts": "{:.1f}", "PPG": "{:.1f}"}),
                    use_container_width=True, hide_index=True, height=600,
                )
    else:
        st.warning("No data available.")

# --- Season Comparison ---
with tab_compare:
    if compare_season and compare_season != season:
        with st.spinner(f"Comparing {season} vs {compare_season}..."):
            primary = get_season_leaders(season, scoring=scoring, limit=100)
            compare = get_season_leaders(compare_season, scoring=scoring, limit=100)

        if primary and compare:
            p_df = pd.DataFrame(primary)
            c_df = pd.DataFrame(compare)

            merged = p_df.merge(c_df, on=["player_id", "player_name", "position"],
                                suffixes=(f"_{season}", f"_{compare_season}"), how="inner")

            if not merged.empty:
                merged["ppg_change"] = merged[f"fantasy_ppg_{season}"] - merged[f"fantasy_ppg_{compare_season}"]
                merged = merged.sort_values("ppg_change", ascending=False)

                col_left, col_right = st.columns(2)
                with col_left:
                    st.markdown("**📈 Biggest PPG Risers**")
                    risers = merged.head(15)[["player_name", "position",
                                               f"fantasy_ppg_{compare_season}",
                                               f"fantasy_ppg_{season}", "ppg_change"]].copy()
                    risers.columns = ["Player", "Pos", f"{compare_season} PPG", f"{season} PPG", "Change"]
                    st.dataframe(
                        risers.style.format({
                            f"{compare_season} PPG": "{:.1f}",
                            f"{season} PPG": "{:.1f}",
                            "Change": "{:+.1f}",
                        }),
                        use_container_width=True, hide_index=True,
                    )

                with col_right:
                    st.markdown("**📉 Biggest PPG Fallers**")
                    fallers = merged.tail(15).sort_values("ppg_change")[["player_name", "position",
                                                                          f"fantasy_ppg_{compare_season}",
                                                                          f"fantasy_ppg_{season}", "ppg_change"]].copy()
                    fallers.columns = ["Player", "Pos", f"{compare_season} PPG", f"{season} PPG", "Change"]
                    st.dataframe(
                        fallers.style.format({
                            f"{compare_season} PPG": "{:.1f}",
                            f"{season} PPG": "{:.1f}",
                            "Change": "{:+.1f}",
                        }),
                        use_container_width=True, hide_index=True,
                    )
            else:
                st.info("No overlapping players found.")
        else:
            st.warning("Could not load comparison data.")
    else:
        st.info("Select a different comparison season in the sidebar.")
