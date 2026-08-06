"""⚔️ Sit/Start Compare — Head-to-head player comparison for lineup decisions."""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from utils.api import search_players, get_weekly_stats, compare_players

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

col_a, col_b = st.columns(2)

with col_a:
    search_a = st.text_input("Player A", placeholder="e.g. Jahmyr Gibbs", key="search_a")
with col_b:
    search_b = st.text_input("Player B", placeholder="e.g. Bijan Robinson", key="search_b")

if not search_a or not search_b or len(search_a) < 2 or len(search_b) < 2:
    st.info("Enter two player names above to compare.")
    st.stop()

# Search and select
results_a = search_players(search_a, limit=5)
results_b = search_players(search_b, limit=5)

if not results_a or not results_b:
    st.warning("Could not find one or both players.")
    st.stop()

col_a2, col_b2 = st.columns(2)
with col_a2:
    opts_a = {f"{p['player_name']} ({p['position']}, {p['current_team'] or 'FA'})": p["player_id"] for p in results_a}
    sel_a = st.selectbox("Select Player A", list(opts_a.keys()), key="sel_a")
    pid_a = opts_a[sel_a]
with col_b2:
    opts_b = {f"{p['player_name']} ({p['position']}, {p['current_team'] or 'FA'})": p["player_id"] for p in results_b}
    sel_b = st.selectbox("Select Player B", list(opts_b.keys()), key="sel_b")
    pid_b = opts_b[sel_b]

st.markdown("---")

# Compare
with st.spinner("Comparing players..."):
    comparison = compare_players([pid_a, pid_b], season=season, scoring=scoring)

if not comparison or len(comparison) < 2:
    st.warning(f"Could not load comparison data for {season}. Both players need stats in this season.")
    st.stop()

comp_df = pd.DataFrame(comparison)
player_a = comp_df[comp_df["player_id"] == pid_a].iloc[0] if pid_a in comp_df["player_id"].values else None
player_b = comp_df[comp_df["player_id"] == pid_b].iloc[0] if pid_b in comp_df["player_id"].values else None

if player_a is None or player_b is None:
    st.warning("Comparison data incomplete.")
    st.stop()

# Summary cards
col1, col2 = st.columns(2)

with col1:
    st.subheader(f"🅰️ {player_a['player_name']}")
    st.caption(f"{player_a['position']} — {player_a['team']}")
    m1, m2, m3 = st.columns(3)
    m1.metric("PPG", f"{player_a['ppg']:.1f}")
    m2.metric("Floor", f"{player_a['floor']:.1f}")
    m3.metric("Ceiling", f"{player_a['ceiling']:.1f}")
    m4, m5, m6 = st.columns(3)
    m4.metric("Consistency", f"{player_a['consistency_score']:.2f}" if player_a['consistency_score'] else "—")
    m5.metric("Boom Weeks", int(player_a["boom_weeks"]))
    m6.metric("Bust Weeks", int(player_a["bust_weeks"]))
    if player_a["recent_ppg"]:
        st.metric("Recent PPG (Last 3)", f"{player_a['recent_ppg']:.1f}",
                   delta=f"{player_a['recent_ppg'] - player_a['ppg']:.1f} vs season")

with col2:
    st.subheader(f"🅱️ {player_b['player_name']}")
    st.caption(f"{player_b['position']} — {player_b['team']}")
    m1, m2, m3 = st.columns(3)
    m1.metric("PPG", f"{player_b['ppg']:.1f}")
    m2.metric("Floor", f"{player_b['floor']:.1f}")
    m3.metric("Ceiling", f"{player_b['ceiling']:.1f}")
    m4, m5, m6 = st.columns(3)
    m4.metric("Consistency", f"{player_b['consistency_score']:.2f}" if player_b['consistency_score'] else "—")
    m5.metric("Boom Weeks", int(player_b["boom_weeks"]))
    m6.metric("Bust Weeks", int(player_b["bust_weeks"]))
    if player_b["recent_ppg"]:
        st.metric("Recent PPG (Last 3)", f"{player_b['recent_ppg']:.1f}",
                   delta=f"{player_b['recent_ppg'] - player_b['ppg']:.1f} vs season")

# Head-to-head weekly chart
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
        mode="lines+markers", name=player_a["player_name"],
        line=dict(width=3),
    ))
    fig.add_trace(go.Scatter(
        x=wb_df["week"], y=wb_df["fantasy_points"],
        mode="lines+markers", name=player_b["player_name"],
        line=dict(width=3),
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
