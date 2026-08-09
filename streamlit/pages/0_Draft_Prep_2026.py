"""🏈 Draft Prep 2026 — Projections, schedule strength, and draft strategy."""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from utils.api import (get_projections, get_schedule_strength, get_team_schedule,
                        player_dropdown, get_player, get_trajectory)

st.set_page_config(page_title="Draft Prep 2026", page_icon="🏈", layout="wide")
st.title("🏈 2026 Draft Prep")

st.markdown("""
Projections built from weighted historical performance (2023–2025), age curve 
adjustments, and availability trends. Schedule difficulty rated using 2025 defensive 
rankings against the 2026 schedule.
""")

scoring_map = {"PPR": "ppr", "Half-PPR": "half_ppr", "Standard": "standard"}
scoring_label = st.sidebar.selectbox("Scoring Format", ["PPR", "Half-PPR", "Standard"])
scoring = scoring_map[scoring_label]
target_season = st.sidebar.selectbox("Target Season", [2026, 2025])

tab_rankings, tab_schedule, tab_player_card = st.tabs([
    "📊 Projected Rankings", "📅 Schedule Strength", "🔍 Player Draft Card"
])

# ===== Projected Rankings =====
with tab_rankings:
    with st.spinner("Generating projections..."):
        projections = get_projections(season=target_season, scoring=scoring, limit=200)

    if not projections:
        st.warning("No projection data available. Make sure historical data is loaded.")
    else:
        proj_df = pd.DataFrame(projections)

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Target Season", target_season)
        col2.metric("Format", scoring_label)
        col3.metric("Players Projected", len(proj_df))
        top = proj_df.iloc[0]
        col4.metric("Projected #1", f"{top['player_name']} ({top['projected_total']})")

        st.markdown("---")

        pos_tabs = st.tabs(["Overall", "QB", "RB", "WR", "TE"])
        for pos_tab, pos in zip(pos_tabs, ["All", "QB", "RB", "WR", "TE"]):
            with pos_tab:
                if pos == "All":
                    pdf = proj_df.copy()
                    rank_col = "overall_rank"
                else:
                    pdf = proj_df[proj_df["position"] == pos].copy()
                    rank_col = "pos_rank"

                if pdf.empty:
                    st.info(f"No {pos} projections.")
                    continue

                display = pdf[[rank_col, "player_name", "position", "team", "age",
                               "projected_ppg", "projected_games", "projected_total",
                               "last_season_ppg", "age_multiplier", "opportunities_pg"]].copy()
                display.columns = ["Rank", "Player", "Pos", "Team", "Age",
                                   "Proj PPG", "Proj GP", "Proj Total",
                                   "2025 PPG", "Age Adj", "Opps/G"]
                st.dataframe(
                    display.style.format({
                        "Proj PPG": "{:.1f}", "Proj Total": "{:.1f}",
                        "2025 PPG": "{:.1f}", "Age Adj": "{:.2f}", "Opps/G": "{:.1f}",
                    }),
                    use_container_width=True, hide_index=True, height=600,
                )

                chart = pdf.head(20)
                fig = px.bar(chart, x="player_name", y="projected_ppg",
                             color="position" if pos == "All" else None,
                             text="projected_ppg",
                             hover_data={"team": True, "age": True, "projected_total": ":.1f",
                                         "last_season_ppg": ":.1f"},
                             labels={"player_name": "", "projected_ppg": "Projected PPG"})
                fig.update_traces(texttemplate="%{text:.1f}", textposition="outside")
                fig.update_layout(xaxis_tickangle=-45, height=500,
                                  title=f"{'Overall' if pos == 'All' else pos} — Projected PPG for {target_season}")
                st.plotly_chart(fig, use_container_width=True)

                if pos != "All":
                    st.subheader("Projection vs Age")
                    fig = px.scatter(pdf, x="age", y="projected_ppg", size="projected_total",
                                     hover_name="player_name",
                                     hover_data={"team": True, "age_multiplier": ":.2f", "projected_total": ":.1f"},
                                     labels={"age": "Age", "projected_ppg": "Projected PPG"})
                    fig.update_layout(height=450)
                    st.plotly_chart(fig, use_container_width=True)

# ===== Schedule Strength =====
with tab_schedule:
    st.markdown(f"""
    **How hard is each team's {target_season} schedule by position?**  
    Based on {target_season - 1} defensive rankings. Positive = easy matchups.
    """)

    sched_position = st.selectbox("Position", ["QB", "RB", "WR", "TE"], key="sched_pos")

    with st.spinner("Loading schedule strength..."):
        sched_data = get_schedule_strength(season=target_season, position=sched_position, scoring=scoring)

    if sched_data:
        sched_df = pd.DataFrame(sched_data)
        sched_df = sched_df.sort_values("schedule_strength", ascending=False)

        fig = px.bar(sched_df, y="team", x="schedule_strength", orientation="h",
                     color="schedule_strength",
                     color_continuous_scale=["red", "yellow", "green"],
                     text="schedule_strength",
                     hover_data={"easy_weeks": True, "hard_weeks": True},
                     labels={"team": "", "schedule_strength": "Schedule Strength"})
        fig.update_traces(texttemplate="%{text:+.2f}", textposition="outside")
        fig.update_layout(height=max(500, len(sched_df) * 25),
                          yaxis=dict(autorange="reversed"), coloraxis_showscale=False,
                          title=f"{sched_position} Schedule Strength — {target_season}")
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        st.subheader("Week-by-Week Matchup Preview")
        team_select = st.selectbox("Select Team", sched_df["team"].tolist(), key="team_wk")

        team_detail = get_team_schedule(team_select, season=target_season,
                                         position=sched_position, scoring=scoring)
        if team_detail and "weekly_matchups" in team_detail:
            wk_df = pd.DataFrame(team_detail["weekly_matchups"])
            colors = ["green" if r > 1 else "red" if r < -1 else "gray" for r in wk_df["matchup_rating"]]
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=wk_df["week"], y=wk_df["matchup_rating"], marker_color=colors,
                text=[f"vs {opp}" for opp in wk_df["opponent"]], textposition="outside",
            ))
            fig.add_hline(y=0, line_dash="dash", line_color="white", line_width=0.5)
            fig.update_layout(title=f"{team_select} — {sched_position} Matchup by Week",
                              xaxis_title="Week", yaxis_title="Rating (+ easy, - hard)", height=400)
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning(f"No schedule data for {target_season}.")

# ===== Player Draft Card =====
with tab_player_card:
    st.markdown("Search a player to see their draft profile with projection and schedule.")

    pid, pname = player_dropdown("Select a player", "draft_card_player")

    if pid:
        player = get_player(pid)
        if not player:
            st.error("Could not load player details.")
        else:
            st.markdown("---")

            # Load projections if not already loaded
            if "projections" not in dir() or not projections:
                projections = get_projections(season=target_season, scoring=scoring, limit=200)

            proj_match = [p for p in (projections or []) if p["player_id"] == pid]

            col_left, col_right = st.columns(2)

            with col_left:
                st.subheader(player["player_name"])
                st.caption(f"{player['position']} — {player.get('current_team') or 'FA'}")

                if proj_match:
                    pm = proj_match[0]
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Projected PPG", f"{pm['projected_ppg']:.1f}")
                    m2.metric("Projected Total", f"{pm['projected_total']:.1f}")
                    m3.metric("Overall Rank", f"#{pm['overall_rank']}")
                    m4, m5, m6 = st.columns(3)
                    m4.metric("Position Rank", f"{pm['position']}{pm['pos_rank']}")
                    m5.metric("Age", pm["age"] or "—")
                    m6.metric("Age Adjustment", f"{pm['age_multiplier']:.0%}")
                    m7, m8, m9 = st.columns(3)
                    m7.metric("2025 PPG", f"{pm['last_season_ppg']:.1f}")
                    m8.metric("Proj Games", pm["projected_games"])
                    m9.metric("Opps/G", f"{pm['opportunities_pg']:.1f}")
                else:
                    st.info("No projection available (may not have enough recent history).")

            with col_right:
                trajectory = get_trajectory(pid, scoring=scoring)
                if trajectory:
                    traj_df = pd.DataFrame(trajectory)
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=traj_df["season"], y=traj_df["ppg"],
                        mode="lines+markers+text", text=traj_df["ppg"],
                        textposition="top center", line=dict(width=3), name="Actual PPG",
                    ))
                    if proj_match:
                        fig.add_trace(go.Scatter(
                            x=[target_season], y=[proj_match[0]["projected_ppg"]],
                            mode="markers+text", text=[f"{proj_match[0]['projected_ppg']:.1f}"],
                            textposition="top center",
                            marker=dict(size=14, symbol="star", color="gold"),
                            name=f"{target_season} Projection",
                        ))
                    fig.update_layout(title="Career Arc + Projection",
                                      xaxis_title="Season", yaxis_title="PPG", height=350)
                    fig.update_xaxes(dtick=1, tickformat="d")
                    st.plotly_chart(fig, use_container_width=True)

            # Schedule
            if player.get("current_team"):
                st.markdown("---")
                st.subheader(f"{target_season} Schedule — {player['current_team']}")
                team_sched = get_team_schedule(
                    player["current_team"], season=target_season,
                    position=player["position"], scoring=scoring,
                )
                if team_sched and "weekly_matchups" in team_sched:
                    wk_df = pd.DataFrame(team_sched["weekly_matchups"])
                    colors = ["green" if r > 1 else "red" if r < -1 else "gray" for r in wk_df["matchup_rating"]]
                    fig = go.Figure()
                    fig.add_trace(go.Bar(
                        x=wk_df["week"], y=wk_df["matchup_rating"], marker_color=colors,
                        text=[f"vs {opp}" for opp in wk_df["opponent"]], textposition="outside",
                    ))
                    fig.add_hline(y=0, line_dash="dash", line_color="white", line_width=0.5)
                    fig.update_layout(title=f"Matchup Difficulty for {player['position']}s",
                                      xaxis_title="Week", yaxis_title="Rating", height=350)
                    st.plotly_chart(fig, use_container_width=True)
                    easy = sum(1 for r in wk_df["matchup_rating"] if r > 1)
                    hard = sum(1 for r in wk_df["matchup_rating"] if r < -1)
                    st.caption(f"📅 {easy} easy weeks | {hard} hard weeks | {len(wk_df)} total games")
    else:
        st.info("Select a player to view their draft card.")
