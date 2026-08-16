"""Start/Sit Advisor — who do I start this week?"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.api import (
    compare_players,
    get_defensive_rankings,
    get_team_defense,
    get_weekly_stats,
    player_dropdown,
)
from utils.components import (
    POSITION_COLORS,
    api_guard,
    inject_custom_css,
    position_badge,
    recommendation_badge,
    render,
    section_header,
    sidebar,
    style_fig,
    verdict,
)

st.set_page_config(page_title="Start/Sit Advisor", page_icon="⚖️", layout="wide")
inject_custom_css()

scoring, season = sidebar(default_season=2025)

st.markdown(
    '<div style="font-size:1.9rem;font-weight:800;color:#f1f5f9">⚖️ Start / Sit Advisor</div>'
    '<div style="color:#94a3b8;margin-bottom:22px">'
    'Which matchups to attack, and who to start when it is close.</div>',
    unsafe_allow_html=True,
)


# =========================================================================
# A) Matchup heat map
# =========================================================================

section_header(f"Matchup Heat Map — {season}")

defense = get_defensive_rankings(season=season, scoring=scoring)

if api_guard(defense, "defensive rankings"):
    ddf = pd.DataFrame(defense)
    ddf["avg_pts_allowed"] = pd.to_numeric(ddf["avg_pts_allowed"], errors="coerce")

    pivot = ddf.pivot_table(index="defense", columns="position",
                            values="avg_pts_allowed", aggfunc="mean")
    pivot = pivot.reindex(columns=[c for c in ["QB", "RB", "WR", "TE"]
                                   if c in pivot.columns])
    # Rank so the color scale reads consistently across positions
    pivot = pivot.sort_values(by=pivot.columns[0], ascending=False)

    fig = go.Figure(data=go.Heatmap(
        z=pivot.values,
        x=pivot.columns.tolist(),
        y=pivot.index.tolist(),
        colorscale=[[0, "#e74c3c"], [0.5, "#1e293b"], [1, "#2ecc71"]],
        hovertemplate="<b>%{y}</b> vs %{x}<br>%{z:.1f} pts allowed/game<extra></extra>",
        colorbar=dict(title="PPG<br>allowed"),
    ))
    fig.update_layout(
        title="Fantasy points allowed per game by defense and position",
        xaxis_title="Position", yaxis_title="Defense",
    )
    st.plotly_chart(style_fig(fig, height=760, showlegend=False),
                    use_container_width=True)
    st.caption(
        "Green = the defense gives up more points to that position, so it is a "
        "matchup to exploit. Red = avoid."
    )


# =========================================================================
# B) Start/Sit comparison
# =========================================================================

st.write("")
section_header("Start / Sit Comparison")

pos_filter = st.selectbox(
    "Filter players by position (optional)",
    ["All", "QB", "RB", "WR", "TE"], index=0, key="ss_pos",
)
pf = None if pos_filter == "All" else pos_filter

c1, c2 = st.columns(2)
with c1:
    pid_a, name_a = player_dropdown("Player A", key="ss_a", position_filter=pf)
with c2:
    pid_b, name_b = player_dropdown("Player B", key="ss_b", position_filter=pf)


def _classify(row, other) -> str:
    """Start / Flex / Sit from PPG, consistency and floor versus the alternative."""
    ppg = float(row.get("ppg") or 0)
    other_ppg = float(other.get("ppg") or 0)
    cons = float(row.get("consistency_score") or 0)
    if ppg >= other_ppg + 1.5:
        return "start"
    if ppg <= other_ppg - 1.5:
        return "sit"
    return "start" if cons >= float(other.get("consistency_score") or 0) else "flex"


if pid_a and pid_b:
    if pid_a == pid_b:
        st.warning("Pick two different players to compare.")
    else:
        rows = compare_players([pid_a, pid_b], season=season, scoring=scoring)
        if not api_guard(rows, f"{season} comparison data"):
            st.stop()

        by_id = {r["player_id"]: r for r in rows}
        a, b = by_id.get(pid_a), by_id.get(pid_b)

        if not a or not b:
            missing = name_a if not a else name_b
            st.warning(f"No {season} regular-season games found for {missing}.")
        else:
            rec_a, rec_b = _classify(a, b), _classify(b, a)

            cards = st.columns(2)
            for col, p, rec in ((cards[0], a, rec_a), (cards[1], b, rec_b)):
                with col:
                    render(f"""
                        <div class="player-card">
                            <div style="margin-bottom:10px">
                                {position_badge(p['position'])}
                                <span style="font-size:1.15rem;font-weight:700;
                                             color:#f1f5f9">{p['player_name']}</span>
                                <span style="color:#64748b;margin-left:6px">{p['team']}</span>
                                <div style="margin-top:10px">{recommendation_badge(rec)}</div>
                            </div>
                        </div>
                    """)
                    m1, m2, m3 = st.columns(3)
                    m1.metric("PPG", f"{float(p['ppg']):.1f}")
                    m2.metric("Floor", f"{float(p['floor']):.1f}")
                    m3.metric("Ceiling", f"{float(p['ceiling']):.1f}")
                    m4, m5, m6 = st.columns(3)
                    m4.metric("Consistency", f"{float(p['consistency_score'] or 0):.2f}")
                    games = int(p["games_played"]) or 1
                    m5.metric("Boom %", f"{100 * int(p['boom_weeks']) / games:.0f}%")
                    m6.metric("Bust %", f"{100 * int(p['bust_weeks']) / games:.0f}%")
                    if p.get("recent_ppg") is not None:
                        st.caption(f"Last 3 weeks: **{float(p['recent_ppg']):.1f}** PPG")

            # --- Weekly overlay ---------------------------------------
            wa = get_weekly_stats(pid_a, season=season, scoring=scoring)
            wb = get_weekly_stats(pid_b, season=season, scoring=scoring)
            if wa or wb:
                fig = go.Figure()
                for w, nm, color in ((wa, a["player_name"], "#3b82f6"),
                                     (wb, b["player_name"], "#f39c12")):
                    if not w:
                        continue
                    wdf = pd.DataFrame(w)
                    ycol = "fantasy_points" if "fantasy_points" in wdf.columns else wdf.columns[-1]
                    fig.add_trace(go.Scatter(
                        x=wdf["week"], y=pd.to_numeric(wdf[ycol], errors="coerce"),
                        name=nm, mode="lines+markers",
                        line=dict(color=color, width=2.5),
                    ))
                fig.update_layout(title=f"Week-by-week fantasy points — {season}",
                                  xaxis_title="Week", yaxis_title="Fantasy points")
                fig.update_xaxes(dtick=1)
                st.plotly_chart(style_fig(fig, height=340), use_container_width=True)

            # --- Verdict ----------------------------------------------
            winner, loser = (a, b) if float(a["ppg"]) >= float(b["ppg"]) else (b, a)
            gap = abs(float(a["ppg"]) - float(b["ppg"]))
            w_cons = float(winner["consistency_score"] or 0)
            l_cons = float(loser["consistency_score"] or 0)

            if gap < 1.0:
                lead = (f"This is close — {gap:.1f} PPG separates them. "
                        f"The tiebreaker is consistency.")
            else:
                lead = (f"**{winner['player_name']}** by {gap:.1f} PPG "
                        f"({float(winner['ppg']):.1f} vs {float(loser['ppg']):.1f}).")

            cons_note = (
                f"{winner['player_name']} is also steadier "
                f"(consistency {w_cons:.2f} vs {l_cons:.2f})."
                if w_cons >= l_cons else
                f"But {loser['player_name']} is the steadier option "
                f"(consistency {l_cons:.2f} vs {w_cons:.2f}) — worth it if you need a floor."
            )

            floor_note = (
                f"Floors: {winner['player_name']} {float(winner['floor']):.1f}, "
                f"{loser['player_name']} {float(loser['floor']):.1f}. "
                f"Ceilings: {float(winner['ceiling']):.1f} and "
                f"{float(loser['ceiling']):.1f}."
            )

            verdict(f"**Verdict —** {lead} {cons_note}<br><br>{floor_note}")


# =========================================================================
# C) DST rankings
# =========================================================================

st.write("")
section_header(f"DST Rankings — {season}")

team_def = get_team_defense(season=season)

if not team_def:
    st.info(
        "Team defense data is unavailable for this season. It comes from "
        "`mart.team_defense` via `/advanced/team-defense`."
    )
else:
    tdf = pd.DataFrame(team_def)
    for c in ["sacks_pg", "interceptions_pg", "fumbles_forced_pg", "qb_hits_pg",
              "pass_defended_pg", "tfl_pg", "dst_score"]:
        if c in tdf.columns:
            tdf[c] = pd.to_numeric(tdf[c], errors="coerce")

    tdf = tdf.sort_values("dst_score", ascending=False).reset_index(drop=True)
    tdf.insert(0, "rank", tdf.index + 1)

    top = st.columns(3)
    for col, (_, r) in zip(top, tdf.head(3).iterrows()):
        with col:
            render(f"""
                <div class="player-card">
                    <div style="display:flex;justify-content:space-between;
                                align-items:center">
                        <div>
                            <span style="color:#64748b;font-size:0.8rem">#{r['rank']}</span>
                            {position_badge('DST')}
                            <span style="font-size:1.1rem;font-weight:700;
                                         color:#f1f5f9">{r['team']}</span>
                        </div>
                        {recommendation_badge('pickup')}
                    </div>
                    <div style="margin-top:10px;font-size:0.85rem;color:#94a3b8">
                        {r['sacks_pg']:.1f} sacks · {r['interceptions_pg']:.1f} INT ·
                        {r['fumbles_forced_pg']:.1f} FF per game
                    </div>
                </div>
            """)

    st.write("")
    show_cols = [c for c in ["rank", "team", "games", "dst_score", "sacks_pg",
                             "qb_hits_pg", "interceptions_pg", "pass_defended_pg",
                             "fumbles_forced_pg", "tfl_pg", "pressure_pg",
                             "coverage_pg"] if c in tdf.columns]
    st.dataframe(tdf[show_cols], use_container_width=True, hide_index=True)
    st.caption(
        "DST score = sacks + interceptions + forced fumbles per game — the three "
        "events most fantasy scoring systems reward. Sorted best to worst."
    )
