"""🔍 Player Lookup — Search, compare, and analyze players."""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from utils.api import (player_dropdown, get_player, get_season_stats,
                        get_weekly_stats, get_trajectory, compare_players)

st.set_page_config(page_title="Player Lookup", page_icon="🔍", layout="wide")
st.title("🔍 Player Lookup")

scoring_map = {"PPR": "ppr", "Half-PPR": "half_ppr", "Standard": "standard"}
scoring_label = st.sidebar.selectbox("Scoring Format", ["PPR", "Half-PPR", "Standard"])
scoring = scoring_map[scoring_label]
compare_mode = st.sidebar.toggle("Compare Two Players", value=False)


def show_player_header(player: dict):
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Position", player.get("position", "—"))
    col2.metric("Team", player.get("current_team", "FA"))
    col3.metric("College", player.get("college", "—"))
    col4.metric("Draft", f"Rd {player.get('draft_round', '—')} Pk {player.get('draft_pick', '—')}")
    col5.metric("Rookie Year", player.get("rookie_year", "—"))


def show_single_player(player_id: str, player: dict):
    show_player_header(player)

    tab_seasons, tab_weekly, tab_trajectory = st.tabs(["📊 Season Stats", "📅 Weekly Breakdown", "📈 Career Trajectory"])

    with tab_seasons:
        season_stats = get_season_stats(player_id, scoring=scoring)
        if season_stats:
            season_df = pd.DataFrame(season_stats)
            display_cols = {
                "season": "Season", "team": "Team", "games_played": "GP",
                "fantasy_points": "Fantasy Pts", "fantasy_ppg": "PPG",
                "passing_yards": "Pass Yds", "passing_tds": "Pass TD", "interceptions": "INT",
                "rushing_yards": "Rush Yds", "rushing_tds": "Rush TD",
                "receptions": "Rec", "targets": "Tgt",
                "receiving_yards": "Rec Yds", "receiving_tds": "Rec TD",
            }
            show_df = season_df[list(display_cols.keys())].copy()
            show_df.columns = list(display_cols.values())
            st.dataframe(
                show_df.style.format({
                    "Fantasy Pts": "{:.1f}", "PPG": "{:.1f}",
                    "Pass Yds": "{:.0f}", "Rush Yds": "{:.0f}", "Rec Yds": "{:.0f}",
                }),
                use_container_width=True, hide_index=True,
            )
            if len(season_df) > 1:
                fig = px.bar(season_df, x="season", y="fantasy_ppg", text="fantasy_ppg",
                             labels={"season": "Season", "fantasy_ppg": "PPG"},
                             title=f"PPG by Season ({scoring_label})")
                fig.update_traces(texttemplate="%{text:.1f}", textposition="outside")
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No season stats available.")

    with tab_weekly:
        season_stats = get_season_stats(player_id, scoring=scoring)
        available_seasons = [s["season"] for s in season_stats] if season_stats else [2025]
        week_season = st.selectbox("Select season", available_seasons, key=f"wk_{player_id}")

        weekly = get_weekly_stats(player_id, season=week_season, scoring=scoring)
        if weekly:
            weekly_df = pd.DataFrame(weekly)
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=weekly_df["week"], y=weekly_df["fantasy_points"],
                name="Fantasy Points", text=weekly_df["fantasy_points"].round(1),
                textposition="outside",
            ))
            avg = weekly_df["fantasy_points"].mean()
            fig.add_hline(y=avg, line_dash="dash", line_color="red", annotation_text=f"Avg: {avg:.1f}")
            fig.add_hline(y=20, line_dash="dot", line_color="green", annotation_text="Boom (20+)",
                           annotation_position="top right")
            fig.add_hline(y=8, line_dash="dot", line_color="orange", annotation_text="Bust (<8)",
                           annotation_position="bottom right")
            fig.update_layout(title=f"Week-by-Week — {week_season} ({scoring_label})",
                              xaxis_title="Week", yaxis_title="Fantasy Points", height=450)
            st.plotly_chart(fig, use_container_width=True)

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("PPG", f"{avg:.1f}")
            col2.metric("Floor", f"{weekly_df['fantasy_points'].min():.1f}")
            col3.metric("Ceiling", f"{weekly_df['fantasy_points'].max():.1f}")
            boom_pct = (weekly_df["fantasy_points"] >= 20).sum() / len(weekly_df) * 100
            col4.metric("Boom Rate", f"{boom_pct:.0f}%")

            week_display = {
                "week": "Wk", "opponent": "Opp", "fantasy_points": "FP",
                "passing_yards": "Pass Yds", "passing_tds": "Pass TD", "interceptions": "INT",
                "rushing_yards": "Rush Yds", "rushing_tds": "Rush TD",
                "receptions": "Rec", "targets": "Tgt",
                "receiving_yards": "Rec Yds", "receiving_tds": "Rec TD",
            }
            week_show = weekly_df[list(week_display.keys())].copy()
            week_show.columns = list(week_display.values())
            st.dataframe(
                week_show.style.format({"FP": "{:.1f}", "Pass Yds": "{:.0f}", "Rush Yds": "{:.0f}", "Rec Yds": "{:.0f}"}),
                use_container_width=True, hide_index=True,
            )
        else:
            st.info(f"No weekly data for {week_season}.")

    with tab_trajectory:
        trajectory = get_trajectory(player_id, scoring=scoring)
        if trajectory and len(trajectory) > 0:
            traj_df = pd.DataFrame(trajectory)
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=traj_df["season"], y=traj_df["ppg"], mode="lines+markers+text",
                text=traj_df["ppg"], textposition="top center", name="PPG", line=dict(width=3),
            ))
            fig.update_layout(title="Fantasy PPG Trajectory", xaxis_title="Season",
                              yaxis_title="PPG", height=400)
            st.plotly_chart(fig, use_container_width=True)

            if "opportunities_pg" in traj_df.columns:
                fig2 = go.Figure()
                fig2.add_trace(go.Bar(x=traj_df["season"], y=traj_df["targets_pg"], name="Targets/G"))
                fig2.add_trace(go.Bar(x=traj_df["season"], y=traj_df["carries_pg"], name="Carries/G"))
                fig2.update_layout(title="Opportunity Trend", xaxis_title="Season",
                                   yaxis_title="Per Game", barmode="stack", height=400)
                st.plotly_chart(fig2, use_container_width=True)

            traj_display = traj_df[["season", "team", "games_played", "total_points", "ppg",
                                     "opportunities_pg", "targets_pg", "carries_pg"]].copy()
            traj_display.columns = ["Season", "Team", "GP", "Total Pts", "PPG", "Opps/G", "Tgt/G", "Car/G"]
            st.dataframe(
                traj_display.style.format({
                    "Total Pts": "{:.1f}", "PPG": "{:.1f}",
                    "Opps/G": "{:.1f}", "Tgt/G": "{:.1f}", "Car/G": "{:.1f}",
                }),
                use_container_width=True, hide_index=True,
            )
        else:
            st.info("No trajectory data available.")


def show_comparison(pid_a: str, pid_b: str):
    season = st.selectbox("Comparison Season", [2025, 2024, 2023, 2022, 2021], key="comp_season")

    with st.spinner("Comparing players..."):
        comp = compare_players([pid_a, pid_b], season=season, scoring=scoring)

    if not comp or len(comp) < 2:
        st.warning(f"Both players need stats in {season} to compare.")
        return

    comp_df = pd.DataFrame(comp)
    pa = comp_df[comp_df["player_id"] == pid_a].iloc[0] if pid_a in comp_df["player_id"].values else None
    pb = comp_df[comp_df["player_id"] == pid_b].iloc[0] if pid_b in comp_df["player_id"].values else None

    if pa is None or pb is None:
        st.warning("Comparison data incomplete.")
        return

    col1, col2 = st.columns(2)
    for col, p, emoji in [(col1, pa, "🅰️"), (col2, pb, "🅱️")]:
        with col:
            st.subheader(f"{emoji} {p['player_name']}")
            st.caption(f"{p['position']} — {p['team']}")
            m1, m2, m3 = st.columns(3)
            m1.metric("PPG", f"{p['ppg']:.1f}")
            m2.metric("Floor", f"{p['floor']:.1f}")
            m3.metric("Ceiling", f"{p['ceiling']:.1f}")
            m4, m5, m6 = st.columns(3)
            m4.metric("Consistency", f"{p['consistency_score']:.2f}" if p['consistency_score'] else "—")
            m5.metric("Boom Wks", int(p["boom_weeks"]))
            m6.metric("Bust Wks", int(p["bust_weeks"]))
            if p["recent_ppg"]:
                st.metric("Recent PPG (Last 3)", f"{p['recent_ppg']:.1f}",
                           delta=f"{p['recent_ppg'] - p['ppg']:.1f} vs season")

    st.markdown("---")
    weekly_a = get_weekly_stats(pid_a, season=season, scoring=scoring)
    weekly_b = get_weekly_stats(pid_b, season=season, scoring=scoring)

    if weekly_a and weekly_b:
        wa_df = pd.DataFrame(weekly_a)
        wb_df = pd.DataFrame(weekly_b)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=wa_df["week"], y=wa_df["fantasy_points"],
                                  mode="lines+markers", name=pa["player_name"], line=dict(width=3)))
        fig.add_trace(go.Scatter(x=wb_df["week"], y=wb_df["fantasy_points"],
                                  mode="lines+markers", name=pb["player_name"], line=dict(width=3)))
        fig.add_hline(y=20, line_dash="dot", line_color="green", annotation_text="Boom")
        fig.add_hline(y=8, line_dash="dot", line_color="orange", annotation_text="Bust")
        fig.update_layout(title=f"Weekly Fantasy Points — {season} ({scoring_label})",
                          xaxis_title="Week", yaxis_title="Fantasy Points", height=450)
        st.plotly_chart(fig, use_container_width=True)

    ppg_diff = pa["ppg"] - pb["ppg"]
    if abs(ppg_diff) < 1.5:
        st.info(f"**Toss-up.** {pa['player_name']} ({pa['ppg']:.1f}) and {pb['player_name']} ({pb['ppg']:.1f}) "
                f"are within 1.5 PPG. Consider matchup and recent trend.")
    elif ppg_diff > 0:
        st.success(f"**Edge: {pa['player_name']}** — {ppg_diff:.1f} PPG advantage. "
                   f"Floor {pa['floor']:.1f} vs {pb['floor']:.1f}.")
    else:
        st.success(f"**Edge: {pb['player_name']}** — {abs(ppg_diff):.1f} PPG advantage. "
                   f"Floor {pb['floor']:.1f} vs {pa['floor']:.1f}.")


# ---- Main ----

if compare_mode:
    st.markdown("### Compare Two Players")
    col_a, col_b = st.columns(2)
    with col_a:
        pid_a, name_a = player_dropdown("Player A", "lookup_a")
    with col_b:
        pid_b, name_b = player_dropdown("Player B", "lookup_b")

    if pid_a and pid_b:
        st.markdown("---")
        show_comparison(pid_a, pid_b)
    elif pid_a or pid_b:
        st.info("Select both players to compare.")
else:
    pid, name = player_dropdown("Select a player", "lookup_main")
    if pid:
        player = get_player(pid)
        if player:
            st.markdown("---")
            show_single_player(pid, player)
