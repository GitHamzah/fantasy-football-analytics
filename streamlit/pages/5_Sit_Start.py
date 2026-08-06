"""⚔️ Sit/Start Compare — Head-to-head player comparison for lineup decisions."""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from utils.api import player_dropdown, get_weekly_stats, compare_players

st.set_page_config(page_title="Sit/Start Compare", page_icon="⚔️", layout="wide")
st.title("⚔️ Sit/Start Compare")

st.markdown("""
Compare 2 players head-to-head for lineup decisions. See consistency, 
floor/ceiling, recent trends, and weekly performance side by side.
""")

scoring_map = {"PPR": "ppr", "Half-PPR": "half_ppr", "Standard": "standard"}
scoring_label = st.sidebar.selectbox("Scoring Format", ["PPR", "Half-PPR", "Standard"])
scoring = scoring_map[scoring_label]
season = st.sidebar.selectbox("Season", [2025, 2024, 2023, 2022, 2021])

# Position filter for dropdowns
pos_filter = st.sidebar.selectbox("Filter by Position", ["All", "QB", "RB", "WR", "TE"])
pos_val = None if pos_filter == "All" else pos_filter

col_a, col_b = st.columns(2)

with col_a:
    pid_a, name_a = player_dropdown("Player A", "ss_a", position_filter=pos_val)
with col_b:
    pid_b, name_b = player_dropdown("Player B", "ss_b", position_filter=pos_val)

if not pid_a or not pid_b:
    st.info("Select two players above to compare.")
    st.stop()

st.markdown("---")

# Compare
with st.spinner("Comparing players..."):
    comparison = compare_players([pid_a, pid_b], season=season, scoring=scoring)

if not comparison or len(comparison) < 2:
    st.warning(f"Both players need stats in {season} to compare.")
    st.stop()

comp_df = pd.DataFrame(comparison)
player_a = comp_df[comp_df["player_id"] == pid_a].iloc[0] if pid_a in comp_df["player_id"].values else None
player_b = comp_df[comp_df["player_id"] == pid_b].iloc[0] if pid_b in comp_df["player_id"].values else None

if player_a is None or player_b is None:
    st.warning("Comparison data incomplete.")
    st.stop()

# Summary cards
col1, col2 = st.columns(2)

for col, p, emoji in [(col1, player_a, "🅰️"), (col2, player_b, "🅱️")]:
    with col:
        st.subheader(f"{emoji} {p['player_name']}")
        st.caption(f"{p['position']} — {p['team']}")
        m1, m2, m3 = st.columns(3)
        m1.metric("PPG", f"{p['ppg']:.1f}")
        m2.metric("Floor", f"{p['floor']:.1f}")
        m3.metric("Ceiling", f"{p['ceiling']:.1f}")
        m4, m5, m6 = st.columns(3)
        m4.metric("Consistency", f"{p['consistency_score']:.2f}" if p['consistency_score'] else "—")
        m5.metric("Boom Weeks", int(p["boom_weeks"]))
        m6.metric("Bust Weeks", int(p["bust_weeks"]))
        if p["recent_ppg"]:
            st.metric("Recent PPG (Last 3)", f"{p['recent_ppg']:.1f}",
                       delta=f"{p['recent_ppg'] - p['ppg']:.1f} vs season")

# Weekly overlay chart
st.markdown("---")
st.subheader("Week-by-Week Comparison")

weekly_a = get_weekly_stats(pid_a, season=season, scoring=scoring)
weekly_b = get_weekly_stats(pid_b, season=season, scoring=scoring)

if weekly_a and weekly_b:
    wa_df = pd.DataFrame(weekly_a)
    wb_df = pd.DataFrame(weekly_b)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=wa_df["week"], y=wa_df["fantasy_points"],
        mode="lines+markers", name=player_a["player_name"], line=dict(width=3),
    ))
    fig.add_trace(go.Scatter(
        x=wb_df["week"], y=wb_df["fantasy_points"],
        mode="lines+markers", name=player_b["player_name"], line=dict(width=3),
    ))
    fig.add_hline(y=20, line_dash="dot", line_color="green", annotation_text="Boom")
    fig.add_hline(y=8, line_dash="dot", line_color="orange", annotation_text="Bust")
    fig.update_layout(
        title=f"Fantasy Points per Week — {season} ({scoring_label})",
        xaxis_title="Week", yaxis_title="Fantasy Points", height=450,
    )
    st.plotly_chart(fig, use_container_width=True)

# Verdict
st.markdown("---")
st.subheader("Quick Verdict")
ppg_diff = player_a["ppg"] - player_b["ppg"]
a_name = player_a["player_name"]
b_name = player_b["player_name"]

if abs(ppg_diff) < 1.5:
    st.info(f"**Toss-up.** {a_name} ({player_a['ppg']:.1f} ppg) and {b_name} ({player_b['ppg']:.1f} ppg) "
            f"are within 1.5 PPG of each other. Consider matchup and recent trend.")
elif ppg_diff > 0:
    st.success(f"**Edge: {a_name}** — {ppg_diff:.1f} PPG advantage ({player_a['ppg']:.1f} vs {player_b['ppg']:.1f}). "
               f"Floor of {player_a['floor']:.1f} vs {player_b['floor']:.1f}.")
else:
    st.success(f"**Edge: {b_name}** — {abs(ppg_diff):.1f} PPG advantage ({player_b['ppg']:.1f} vs {player_a['ppg']:.1f}). "
               f"Floor of {player_b['floor']:.1f} vs {player_a['floor']:.1f}.")
