"""Draft War Room — who should I draft?"""

import streamlit as st

# TEMPORARY DIAGNOSTIC — surfaces the real import error on Streamlit Cloud
# instead of a blank crash. Remove once the deploy is confirmed healthy.
# Third-party imports are inside the try as well, so a missing plotly/pandas
# on the host is caught here rather than failing above this block.
try:
    import pandas as pd
    import plotly.express as px
    import plotly.graph_objects as go

    from utils.api import (
        get_projections,
        get_vor,
        get_team_schedule,
        get_trajectory,
        get_player_advanced,
        player_dropdown,
    )
    from utils.components import (
        POSITION_COLORS,
        api_guard,
        inject_custom_css,
        matchup_rating_label,
        metric_row,
        player_card_html,
        season_axis,
        section_header,
        sidebar,
        style_fig,
    )
except Exception as e:
    import sys
    import traceback

    st.error(f"Import failed: {type(e).__name__}: {e}")
    st.code(traceback.format_exc(), language="text")
    st.caption(f"Python {sys.version}")
    st.caption(f"sys.path: {sys.path}")
    st.stop()

st.set_page_config(page_title="Draft War Room", page_icon="🏆", layout="wide")
inject_custom_css()

TARGET_SEASON = 2026
LAST_SEASON = TARGET_SEASON - 1

scoring, _ = sidebar(show_season=False)

st.markdown(
    '<div style="font-size:1.9rem;font-weight:800;color:#f1f5f9">🏆 Draft War Room</div>'
    '<div style="color:#94a3b8;margin-bottom:22px">'
    f'{TARGET_SEASON} projections, position scarcity and player draft cards.</div>',
    unsafe_allow_html=True,
)

projections = get_projections(season=TARGET_SEASON, scoring=scoring, limit=300)


# =========================================================================
# A) Draft Strategy Overview
# =========================================================================

section_header("Draft Strategy Overview")

if api_guard(projections, "projections"):
    def _top(pos=None):
        pool = [p for p in projections if not pos or p["position"] == pos]
        return pool[0] if pool else None

    overall, top_qb, top_rb, top_wr = _top(), _top("QB"), _top("RB"), _top("WR")

    def _fmt(p):
        if not p:
            return "—", "n/a"
        return f"{p['projected_ppg']:.1f}", f"{p['player_name']} ({p['team']})"

    metric_row([
        (_fmt(overall)[0], f"#1 Overall · {_fmt(overall)[1]}"),
        (_fmt(top_qb)[0], f"Top QB · {_fmt(top_qb)[1]}"),
        (_fmt(top_rb)[0], f"Top RB · {_fmt(top_rb)[1]}"),
        (_fmt(top_wr)[0], f"Top WR · {_fmt(top_wr)[1]}"),
    ])

    st.write("")

    # --- Position scarcity from VOR -------------------------------------
    vor = get_vor(season=LAST_SEASON, scoring=scoring, limit=200)
    if vor:
        vdf = pd.DataFrame(vor)
        vdf["vor_ppg"] = pd.to_numeric(vdf["vor_ppg"], errors="coerce")
        vdf = vdf.sort_values(["position", "pos_rank"])

        fig = go.Figure()
        for pos in ["QB", "RB", "WR", "TE"]:
            sub = vdf[vdf["position"] == pos]
            if sub.empty:
                continue
            fig.add_trace(go.Scatter(
                x=sub["pos_rank"], y=sub["vor_ppg"],
                name=pos, mode="lines+markers",
                line=dict(color=POSITION_COLORS[pos], width=2.5),
                marker=dict(size=5),
                hovertemplate=(
                    f"<b>{pos}%{{customdata[0]}}</b> %{{customdata[1]}}<br>"
                    "VOR: %{y:.1f} PPG<extra></extra>"
                ),
                customdata=sub[["pos_rank", "player_name"]].values,
            ))

        fig.add_hline(y=0, line_dash="dash", line_color="#64748b",
                      annotation_text="replacement level",
                      annotation_font_color="#94a3b8")
        fig.update_layout(
            title=f"Position scarcity — VOR drop-off by position rank ({LAST_SEASON})",
            xaxis_title="Rank within position",
            yaxis_title="Value over replacement (PPG)",
        )
        st.plotly_chart(style_fig(fig, height=420), use_container_width=True)
        st.caption(
            "Draft positions above the replacement line first — the steeper the "
            "drop, the more scarce that position is."
        )
    else:
        st.info(f"No VOR data available for {LAST_SEASON}.")


# =========================================================================
# B) Projected Rankings
# =========================================================================

st.write("")
section_header(f"Projected Rankings — {TARGET_SEASON}")

if projections:
    tabs = st.tabs(["Overall", "QB", "RB", "WR", "TE"])
    for tab, pos in zip(tabs, [None, "QB", "RB", "WR", "TE"]):
        with tab:
            pool = [p for p in projections if not pos or p["position"] == pos]
            if not pool:
                st.info(f"No {pos or 'player'} projections available.")
                continue

            for i, p in enumerate(pool[:10], 1):
                extra = {
                    "Total": f"{p['projected_total']:.0f}",
                    "Games": p["projected_games"],
                }
                if p.get("age"):
                    extra["Age"] = p["age"]
                if p.get("last_season_ppg") is not None:
                    extra[f"{LAST_SEASON} PPG"] = f"{p['last_season_ppg']:.1f}"
                extra["Method"] = p.get("method", "—")

                st.markdown(
                    player_card_html(
                        name=p["player_name"], position=p["position"],
                        team=p["team"] or "FA",
                        projected_ppg=float(p["projected_ppg"]),
                        rank=i, extra_stats=extra,
                    ),
                    unsafe_allow_html=True,
                )

            with st.expander("Full Rankings Table"):
                df = pd.DataFrame(pool)
                cols = [c for c in [
                    "overall_rank", "pos_rank", "player_name", "position", "team",
                    "age", "projected_ppg", "projected_games", "projected_total",
                    "last_season_ppg", "last_season_games", "method",
                ] if c in df.columns]
                st.dataframe(df[cols], use_container_width=True, hide_index=True)


# =========================================================================
# C) Player Draft Card
# =========================================================================

st.write("")
section_header("Player Draft Card")

player_id, player_name = player_dropdown("Search for a player", key="draft_card_player")

if player_id:
    proj = next((p for p in projections if p["player_id"] == player_id), None)
    traj = get_trajectory(player_id, scoring=scoring)

    if not proj and not traj:
        st.info(f"No projection or history found for {player_name}.")
    else:
        position = (proj or {}).get("position") or (traj[-1]["position"] if traj else "—")
        team = (proj or {}).get("team") or (traj[-1]["team"] if traj else "—")

        left, right = st.columns([1, 1.4])

        with left:
            st.markdown(
                f'<div style="font-size:1.25rem;font-weight:700;color:#f1f5f9">'
                f'{player_name}</div>'
                f'<div style="color:#64748b;margin-bottom:14px">{position} · {team}</div>',
                unsafe_allow_html=True,
            )
            if proj:
                st.metric(f"{TARGET_SEASON} projected PPG", f"{proj['projected_ppg']:.1f}")
                st.metric("Projected total", f"{proj['projected_total']:.0f}")
                st.metric("Projected games", proj["projected_games"])
                c1, c2 = st.columns(2)
                c1.metric("Overall rank", f"#{proj.get('overall_rank', '—')}")
                c2.metric("Position rank", f"{position}{proj.get('pos_rank', '—')}")
                st.caption(
                    f"Method: **{proj.get('method', 'n/a')}**"
                    + (f" · age multiplier {proj['age_multiplier']}"
                       if proj.get("age_multiplier") else "")
                )
            else:
                st.info("No 2026 projection — player may not have qualified.")

        with right:
            if traj:
                tdf = pd.DataFrame(traj)
                tdf["ppg"] = pd.to_numeric(tdf["ppg"], errors="coerce")
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=tdf["season"], y=tdf["ppg"], mode="lines+markers",
                    name="Actual PPG",
                    line=dict(color=POSITION_COLORS.get(position, "#3b82f6"), width=3),
                    marker=dict(size=9),
                ))
                if proj:
                    fig.add_trace(go.Scatter(
                        x=[TARGET_SEASON], y=[float(proj["projected_ppg"])],
                        mode="markers+text", name=f"{TARGET_SEASON} projection",
                        marker=dict(size=20, color="#f1c40f", symbol="star"),
                        text=[f"{proj['projected_ppg']:.1f}"], textposition="top center",
                        textfont=dict(color="#f1c40f"),
                    ))
                fig.update_layout(
                    title="Career trajectory", xaxis_title="Season",
                    yaxis_title="Fantasy PPG",
                )
                st.plotly_chart(season_axis(style_fig(fig, height=330)),
                                use_container_width=True)
            else:
                st.info("No career history available.")

        # --- Schedule difficulty ---------------------------------------
        if team and team != "—" and position in ("QB", "RB", "WR", "TE"):
            sched = get_team_schedule(team, season=TARGET_SEASON,
                                      position=position, scoring=scoring)
            if sched and sched.get("weekly_matchups"):
                sdf = pd.DataFrame(sched["weekly_matchups"])
                fig = px.bar(
                    sdf, x="week", y="matchup_rating",
                    color="matchup_rating",
                    color_continuous_scale=["#e74c3c", "#64748b", "#2ecc71"],
                    color_continuous_midpoint=0,
                    hover_data=["opponent", "home_away", "opp_pts_allowed"],
                    title=f"{team} {position} schedule difficulty — {TARGET_SEASON}",
                )
                fig.update_layout(xaxis_title="Week",
                                  yaxis_title="Matchup rating (+ easier)")
                fig.update_coloraxes(showscale=False)
                st.plotly_chart(style_fig(fig, height=300, showlegend=False),
                                use_container_width=True)

                easy = sched.get("easy_weeks", 0)
                hard = sched.get("hard_weeks", 0)
                st.markdown(
                    f"Season outlook: {matchup_rating_label(sched['schedule_strength'])} "
                    f"&nbsp;·&nbsp; **{easy}** favourable weeks, **{hard}** tough weeks "
                    f"across {sched.get('total_weeks', 0)} games.",
                    unsafe_allow_html=True,
                )
            else:
                st.caption(f"No {TARGET_SEASON} schedule loaded yet for {team}.")

        # --- PFR advanced ----------------------------------------------
        adv = get_player_advanced(player_id)
        if adv:
            with st.expander("Advanced metrics (Pro Football Reference)", expanded=True):
                adf = pd.DataFrame(adv)
                # Only show the stat family that applies to this position
                if position == "QB":
                    cols = ["season", "games", "bad_throw_pct", "pressured_pct",
                            "blitzed_pg", "hurried_pg", "hit_pg", "sacked_pg"]
                elif position == "RB":
                    cols = ["season", "games", "ybc_per_carry", "yac_per_carry",
                            "broken_tackles_pg", "drop_pct"]
                else:
                    cols = ["season", "games", "drop_pct", "target_passer_rating",
                            "rec_broken_tackles_pg"]
                cols = [c for c in cols if c in adf.columns]
                show = adf[cols].copy()
                for pct in ("bad_throw_pct", "pressured_pct", "drop_pct"):
                    if pct in show.columns:
                        show[pct] = (pd.to_numeric(show[pct], errors="coerce") * 100).round(1)
                st.dataframe(show, use_container_width=True, hide_index=True)
                st.caption("Percentage columns shown as percentages (e.g. 18.0 = 18%).")
