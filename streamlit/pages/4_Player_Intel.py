"""Player Intel — how good is this player, really?"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.api import (
    get_defense_by_unit,
    get_player,
    get_player_advanced,
    get_projections,
    get_season_stats,
    get_team_schedule,
    get_trajectory,
    get_weekly_stats,
    player_dropdown,
)
from utils.components import (
    POSITION_COLORS,
    inject_custom_css,
    position_badge,
    recommendation_badge,
    render,
    season_axis,
    section_header,
    sidebar,
    style_fig,
)

st.set_page_config(page_title="Player Intel", page_icon="🔍", layout="wide")
inject_custom_css()

scoring, season = sidebar(default_season=2025)
TARGET_SEASON = 2026

with st.sidebar:
    st.markdown("---")
    compare_mode = st.toggle("Comparison mode", value=False, key="pi_compare")

st.markdown(
    '<div style="font-size:1.9rem;font-weight:800;color:#f1f5f9">🔍 Player Intel</div>'
    '<div style="color:#94a3b8;margin-bottom:22px">'
    'Everything about one player on a single screen.</div>',
    unsafe_allow_html=True,
)

projections = get_projections(season=TARGET_SEASON, scoring=scoring, limit=300)
proj_by_id = {p["player_id"]: p for p in projections} if projections else {}


def _trend_badge(traj: list) -> tuple[str, str]:
    """Rising / steady / falling from the last two seasons of PPG."""
    if not traj or len(traj) < 2:
        return "flex", "Not enough history to call a trend."
    last = float(traj[-1]["ppg"] or 0)
    prev = float(traj[-2]["ppg"] or 0)
    delta = last - prev
    if delta > 1.5:
        return "start", f"Rising — up {delta:.1f} PPG on last season."
    if delta < -1.5:
        return "sit", f"Falling — down {abs(delta):.1f} PPG on last season."
    return "flex", f"Steady — within {abs(delta):.1f} PPG of last season."


def render_player(player_id: str, player_name: str, key_prefix: str, narrow: bool = False):
    """Render the full intel layout for one player."""
    detail = get_player(player_id) or {}
    traj = get_trajectory(player_id, scoring=scoring)
    proj = proj_by_id.get(player_id)

    position = detail.get("position") or (traj[-1]["position"] if traj else "—")
    team = detail.get("current_team") or (traj[-1]["team"] if traj else "—")
    color = POSITION_COLORS.get(position, "#3b82f6")

    # --- Row 1: header card --------------------------------------------
    rec, rec_reason = _trend_badge(traj)
    season_ppg = next((float(t["ppg"]) for t in traj if t["season"] == season), None) if traj else None

    render(f"""
        <div class="player-card">
            <div style="display:flex;justify-content:space-between;align-items:center">
                <div>
                    {position_badge(position)}
                    <span style="font-size:1.4rem;font-weight:700;color:#f1f5f9">
                        {player_name}</span>
                    <span style="color:#64748b;margin-left:10px">{team}</span>
                </div>
                <div>{recommendation_badge(rec)}</div>
            </div>
            <div style="margin-top:10px;font-size:0.85rem;color:#94a3b8">
                {rec_reason}
            </div>
        </div>
    """)

    m = st.columns(4)
    m[0].metric(f"{TARGET_SEASON} proj PPG",
                f"{proj['projected_ppg']:.1f}" if proj else "—")
    m[1].metric(f"{season} PPG", f"{season_ppg:.1f}" if season_ppg is not None else "—")
    m[2].metric("Age", detail.get("age") or (proj or {}).get("age") or "—")
    draft = detail.get("draft_round")
    m[3].metric("Drafted", f"R{draft} · {detail.get('draft_year', '')}" if draft else "—")

    # --- Row 2: season table + trajectory -------------------------------
    st.write("")
    c1, c2 = st.columns(2)

    with c1:
        st.markdown("**Season by season**")
        seasons = get_season_stats(player_id, scoring=scoring)
        if seasons:
            sdf = pd.DataFrame(seasons)
            keep = [c for c in ["season", "games_played", "total_points", "ppg",
                                "passing_yards", "rushing_yards", "receiving_yards",
                                "receptions", "targets"] if c in sdf.columns]
            st.dataframe(sdf[keep], use_container_width=True, hide_index=True)
        else:
            st.info("No season stats found.")

    with c2:
        st.markdown("**Career trajectory**")
        if traj:
            tdf = pd.DataFrame(traj)
            tdf["ppg"] = pd.to_numeric(tdf["ppg"], errors="coerce")
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=tdf["season"], y=tdf["ppg"], mode="lines+markers",
                name="PPG", line=dict(color=color, width=3), marker=dict(size=9),
            ))
            if proj:
                fig.add_trace(go.Scatter(
                    x=[TARGET_SEASON], y=[float(proj["projected_ppg"])],
                    mode="markers+text", name=f"{TARGET_SEASON} proj",
                    marker=dict(size=20, color="#f1c40f", symbol="star"),
                    text=[f"{proj['projected_ppg']:.1f}"], textposition="top center",
                    textfont=dict(color="#f1c40f"),
                ))
            fig.update_layout(xaxis_title="Season", yaxis_title="Fantasy PPG")
            st.plotly_chart(season_axis(style_fig(fig, height=320)),
                            use_container_width=True,
                            key=f"{key_prefix}_traj")
        else:
            st.info("No trajectory available.")

    # --- Row 3: weekly performance -------------------------------------
    st.write("")
    c3, c4 = st.columns(2)
    weekly = get_weekly_stats(player_id, season=season, scoring=scoring)

    with c3:
        st.markdown(f"**{season} week by week**")
        if weekly:
            wdf = pd.DataFrame(weekly)
            ycol = "fantasy_points" if "fantasy_points" in wdf.columns else wdf.columns[-1]
            wdf[ycol] = pd.to_numeric(wdf[ycol], errors="coerce")
            avg = wdf[ycol].mean()

            fig = px.bar(wdf, x="week", y=ycol,
                         color=ycol,
                         color_continuous_scale=["#e74c3c", "#64748b", "#2ecc71"])
            fig.add_hline(y=20, line_dash="dot", line_color="#2ecc71",
                          annotation_text="boom (20)",
                          annotation_font_color="#2ecc71")
            fig.add_hline(y=8, line_dash="dot", line_color="#e74c3c",
                          annotation_text="bust (8)",
                          annotation_font_color="#e74c3c")
            fig.add_hline(y=avg, line_dash="dash", line_color="#3b82f6",
                          annotation_text=f"avg {avg:.1f}",
                          annotation_font_color="#3b82f6")
            fig.update_layout(xaxis_title="Week", yaxis_title="Fantasy points")
            fig.update_xaxes(dtick=1)
            fig.update_coloraxes(showscale=False)
            st.plotly_chart(style_fig(fig, height=320, showlegend=False),
                            use_container_width=True, key=f"{key_prefix}_weekly")
        else:
            st.info(f"No {season} weekly games found.")

    with c4:
        st.markdown("**Weekly detail**")
        if weekly:
            with st.expander("Show weekly stats table", expanded=not narrow):
                st.dataframe(pd.DataFrame(weekly), use_container_width=True,
                             hide_index=True)
        else:
            st.info("No weekly data.")

    # --- Row 4: schedule + PFR advanced ---------------------------------
    st.write("")
    c5, c6 = st.columns(2)

    with c5:
        st.markdown(f"**{TARGET_SEASON} schedule difficulty**")
        if team and team != "—" and position in ("QB", "RB", "WR", "TE"):
            sched = get_team_schedule(team, season=TARGET_SEASON,
                                      position=position, scoring=scoring)
            if sched and sched.get("weekly_matchups"):
                mdf = pd.DataFrame(sched["weekly_matchups"])
                fig = px.bar(mdf, x="week", y="matchup_rating",
                             color="matchup_rating",
                             color_continuous_scale=["#e74c3c", "#64748b", "#2ecc71"],
                             color_continuous_midpoint=0,
                             hover_data=["opponent", "home_away"])
                fig.update_layout(xaxis_title="Week", yaxis_title="Matchup rating")
                fig.update_xaxes(dtick=1)
                fig.update_coloraxes(showscale=False)
                st.plotly_chart(style_fig(fig, height=300, showlegend=False),
                                use_container_width=True, key=f"{key_prefix}_sched")
            else:
                st.info(f"No {TARGET_SEASON} schedule for {team}.")
        else:
            st.info("Schedule needs a team and a fantasy position.")

    with c6:
        st.markdown("**Advanced metrics (PFR)**")
        adv = get_player_advanced(player_id)
        if adv:
            adf = pd.DataFrame(adv)
            if position == "QB":
                cols = ["season", "games", "bad_throw_pct", "pressured_pct",
                        "blitzed_pg", "hurried_pg", "sacked_pg"]
            elif position == "RB":
                cols = ["season", "games", "ybc_per_carry", "yac_per_carry",
                        "broken_tackles_pg"]
            else:
                cols = ["season", "games", "drop_pct", "target_passer_rating",
                        "rec_broken_tackles_pg"]
            cols = [c for c in cols if c in adf.columns]
            show = adf[cols].copy()
            for pct in ("bad_throw_pct", "pressured_pct", "drop_pct"):
                if pct in show.columns:
                    show[pct] = (pd.to_numeric(show[pct], errors="coerce") * 100).round(1)
            st.dataframe(show, use_container_width=True, hide_index=True)
            st.caption("Percent columns scaled to percentages.")
        else:
            st.info("No PFR advanced coverage for this player.")

    # --- Row 5: defensive matchup preview -------------------------------
    st.write("")
    st.markdown("**Defensive matchup preview**")

    unit = "SECONDARY" if position in ("WR", "TE", "QB") else "FRONT7"
    unit_label = {
        "WR": "opposing secondary coverage",
        "TE": "opposing secondary coverage",
        "QB": "opposing pass rush and coverage",
        "RB": "opposing front seven run defense",
    }.get(position, "opposing defense")

    def_rows = get_defense_by_unit(season=season, unit=unit)
    if def_rows:
        ddf = pd.DataFrame(def_rows)
        if position in ("WR", "TE"):
            cols = ["defense", "games", "completion_pct_allowed",
                    "yards_per_target_allowed", "passer_rating_allowed", "ints_pg"]
            sort_col, asc = "passer_rating_allowed", False
        elif position == "QB":
            cols = ["defense", "games", "sacks_pg", "pressures_pg", "qb_hits_pg",
                    "passer_rating_allowed"]
            sort_col, asc = "pressures_pg", False
        else:
            cols = ["defense", "games", "tackles_pg", "missed_tackle_pct",
                    "sacks_pg", "pressures_pg"]
            sort_col, asc = "missed_tackle_pct", False

        cols = [c for c in cols if c in ddf.columns]
        show = ddf[cols].copy()
        if "completion_pct_allowed" in show.columns:
            show["completion_pct_allowed"] = (
                pd.to_numeric(show["completion_pct_allowed"], errors="coerce") * 100
            ).round(1)
        if "missed_tackle_pct" in show.columns:
            show["missed_tackle_pct"] = (
                pd.to_numeric(show["missed_tackle_pct"], errors="coerce") * 100
            ).round(1)
        if sort_col in show.columns:
            show = show.sort_values(sort_col, ascending=asc)

        st.caption(
            f"Ranking every {unit_label} in {season} — the teams at the top are the "
            f"softest matchups for a {position}."
        )
        st.dataframe(show.head(12), use_container_width=True, hide_index=True)
    else:
        st.info(
            f"No PFR {unit} data for {season}. Served by "
            f"`/advanced/pfr/defense-vs-position`."
        )


# =========================================================================
# Layout: single player or comparison
# =========================================================================

if compare_mode:
    section_header("Compare two players")
    c1, c2 = st.columns(2)
    with c1:
        pid_a, name_a = player_dropdown("Player A", key="pi_a")
    with c2:
        pid_b, name_b = player_dropdown("Player B", key="pi_b")

    if pid_a and pid_b:
        col_a, col_b = st.columns(2)
        with col_a:
            render_player(pid_a, name_a, key_prefix="a", narrow=True)
        with col_b:
            render_player(pid_b, name_b, key_prefix="b", narrow=True)
    else:
        st.info("Pick two players to compare them side by side.")
else:
    pid, name = player_dropdown("Search for a player", key="pi_single")
    if pid:
        render_player(pid, name, key_prefix="single")
    else:
        st.info("Search for a player above to see their full profile.")
