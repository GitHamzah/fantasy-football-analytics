"""Waiver Wire — who should I pick up?"""

import pandas as pd
import streamlit as st

from utils.api import (
    get_defensive_rankings,
    get_opportunity,
    get_schedule_strength,
    get_season_leaders,
    get_team_defense,
    get_weekly_stats,
)
from utils.components import (
    api_guard,
    inject_custom_css,
    matchup_rating_label,
    player_card_html,
    position_badge,
    recommendation_badge,
    render,
    section_header,
    sidebar,
    style_fig,
)

st.set_page_config(page_title="Waiver Wire", page_icon="📈", layout="wide")
inject_custom_css()

scoring, season = sidebar(default_season=2025)
NEXT_SEASON = 2026

st.markdown(
    '<div style="font-size:1.9rem;font-weight:800;color:#f1f5f9">📈 Waiver Wire</div>'
    '<div style="color:#94a3b8;margin-bottom:22px">'
    'Who is heating up, whose schedule is about to soften, and which defense to stream.</div>',
    unsafe_allow_html=True,
)


# =========================================================================
# A) Trending up
# =========================================================================

section_header(f"Trending Up — recent form vs season average ({season})")


@st.cache_data(ttl=300, show_spinner="Scanning recent form...")
def _trending(season: int, scoring: str, pool_size: int = 90) -> pd.DataFrame:
    """Compare each leader's last-3-week PPG to their season PPG."""
    leaders = get_season_leaders(season=season, scoring=scoring, limit=pool_size)
    if not leaders:
        return pd.DataFrame()

    rows = []
    for p in leaders:
        weekly = get_weekly_stats(p["player_id"], season=season, scoring=scoring)
        if not weekly or len(weekly) < 4:
            continue
        wdf = pd.DataFrame(weekly)
        ycol = "fantasy_points" if "fantasy_points" in wdf.columns else wdf.columns[-1]
        wdf[ycol] = pd.to_numeric(wdf[ycol], errors="coerce")
        wdf = wdf.sort_values("week")

        season_ppg = wdf[ycol].mean()
        recent_ppg = wdf[ycol].tail(3).mean()
        rows.append({
            "player_id": p["player_id"],
            "player_name": p["player_name"],
            "position": p["position"],
            "team": p.get("team"),
            "season_ppg": round(float(season_ppg), 1),
            "recent_ppg": round(float(recent_ppg), 1),
            "trend": round(float(recent_ppg - season_ppg), 1),
            "games": len(wdf),
        })

    return pd.DataFrame(rows)


trend_df = _trending(season, scoring)

if not api_guard(None if trend_df.empty else True, "weekly trend data"):
    pass
else:
    opportunity = get_opportunity(season=season, scoring=scoring, limit=200)
    opp_by_id = {o["player_id"]: o for o in opportunity} if opportunity else {}

    tabs = st.tabs(["All", "QB", "RB", "WR", "TE"])
    for tab, pos in zip(tabs, [None, "QB", "RB", "WR", "TE"]):
        with tab:
            sub = trend_df if pos is None else trend_df[trend_df["position"] == pos]
            sub = sub.sort_values("trend", ascending=False).head(10)

            if sub.empty:
                st.info(f"No trending {pos or 'players'} found for {season}.")
                continue

            for i, (_, r) in enumerate(sub.iterrows(), 1):
                extra = {
                    "Recent": f"{r['recent_ppg']:.1f} PPG",
                    "Season": f"{r['season_ppg']:.1f} PPG",
                    "Trend": f"+{r['trend']:.1f}" if r["trend"] > 0 else f"{r['trend']:.1f}",
                }
                o = opp_by_id.get(r["player_id"])
                if o:
                    extra["Targets/g"] = o.get("targets_pg")
                    extra["Carries/g"] = o.get("carries_pg")

                st.markdown(
                    player_card_html(
                        name=r["player_name"], position=r["position"],
                        team=r["team"] or "FA",
                        projected_ppg=float(r["recent_ppg"]),
                        rank=i,
                        rec="pickup" if r["trend"] > 0 else None,
                        extra_stats=extra,
                    ),
                    unsafe_allow_html=True,
                )

            st.caption(
                "PPG shown is the last three weeks. Trend is recent form minus "
                "season average — the widest positive gaps are heating up."
            )


# =========================================================================
# B) Schedule-based pickups
# =========================================================================

st.write("")
section_header(f"Schedule-Based Pickups — easiest {NEXT_SEASON} schedules")

sched = get_schedule_strength(season=NEXT_SEASON, scoring=scoring)

if not sched:
    st.info(
        f"No {NEXT_SEASON} schedule loaded yet, so upcoming-matchup pickups cannot "
        f"be computed. This needs `dim_game` rows for {NEXT_SEASON}."
    )
else:
    sdf = pd.DataFrame(sched)
    sdf["schedule_strength"] = pd.to_numeric(sdf["schedule_strength"], errors="coerce")

    pos_pick = st.selectbox("Position", ["RB", "WR", "TE", "QB"], key="ww_sched_pos")
    sub = sdf[sdf["position"] == pos_pick].sort_values(
        "schedule_strength", ascending=False).head(8)

    if sub.empty:
        st.info(f"No schedule data for {pos_pick}.")
    else:
        for _, r in sub.iterrows():
            weeks = r.get("weekly_matchups") or []
            next4 = weeks[:4] if isinstance(weeks, list) else []
            soft = sum(1 for w in next4 if (w.get("matchup_rating") or 0) > 0.5)
            opps = ", ".join(w.get("opponent", "?") for w in next4)

            render(f"""
                <div class="player-card">
                    <div style="display:flex;justify-content:space-between;
                                align-items:center">
                        <div>
                            {position_badge(pos_pick)}
                            <span style="font-size:1.1rem;font-weight:700;
                                         color:#f1f5f9">{r['team']}</span>
                            <span style="color:#64748b;margin-left:10px">
                                {r['easy_weeks']} easy / {r['hard_weeks']} tough weeks
                            </span>
                        </div>
                        <div>{matchup_rating_label(float(r['schedule_strength']))}</div>
                    </div>
                    <div style="margin-top:8px;font-size:0.85rem;color:#94a3b8">
                        Faces favourable defenses <b style="color:#e2e8f0">{soft} of the
                        next 4</b> weeks — next up: {opps or 'n/a'}
                    </div>
                </div>
            """)

        st.caption(
            f"Target {pos_pick}s on these teams: their schedule rates easiest at "
            f"this position. Rating is points allowed above league average."
        )


# =========================================================================
# C) DST streamers
# =========================================================================

st.write("")
section_header(f"DST Streamers — {season}")

team_def = get_team_defense(season=season)
off_def = get_defensive_rankings(season=season, scoring=scoring)

if not team_def:
    st.info(
        "Team defense data unavailable — served by `/advanced/team-defense` "
        "from `mart.team_defense`."
    )
else:
    tdf = pd.DataFrame(team_def)
    for c in ["sacks_pg", "interceptions_pg", "fumbles_forced_pg", "pressure_pg",
              "coverage_pg", "dst_score"]:
        if c in tdf.columns:
            tdf[c] = pd.to_numeric(tdf[c], errors="coerce")
    tdf = tdf.sort_values("dst_score", ascending=False).reset_index(drop=True)

    # How generous is each team's own offense? Used as the "opponent weakness"
    # signal — defenses facing these offenses are better streams.
    weak_offenses = []
    if off_def:
        odf = pd.DataFrame(off_def)
        odf["avg_pts_allowed"] = pd.to_numeric(odf["avg_pts_allowed"], errors="coerce")
        weak_offenses = (
            odf.groupby("defense")["avg_pts_allowed"].mean()
            .sort_values(ascending=False).head(8).index.tolist()
        )

    cols = st.columns(2)
    for i, (_, r) in enumerate(tdf.head(6).iterrows(), 1):
        with cols[(i - 1) % 2]:
            render(f"""
                <div class="player-card">
                    <div style="display:flex;justify-content:space-between;
                                align-items:center">
                        <div>
                            <span style="color:#64748b;font-size:0.8rem">#{i}</span>
                            {position_badge('DST')}
                            <span style="font-size:1.1rem;font-weight:700;
                                         color:#f1f5f9">{r['team']}</span>
                        </div>
                        {recommendation_badge('pickup')}
                    </div>
                    <div style="margin-top:10px;font-size:0.85rem">
                        <span style="color:#94a3b8">Pressure:</span>
                        <span style="color:#e2e8f0">{r['pressure_pg']:.1f}/g</span> ·
                        <span style="color:#94a3b8">Coverage:</span>
                        <span style="color:#e2e8f0">{r['coverage_pg']:.1f}/g</span> ·
                        <span style="color:#94a3b8">Takeaways:</span>
                        <span style="color:#e2e8f0">
                            {r['interceptions_pg'] + r['fumbles_forced_pg']:.1f}/g</span>
                    </div>
                </div>
            """)

    if weak_offenses:
        st.write("")
        st.markdown(
            '<div style="color:#94a3b8;font-size:0.9rem">'
            '<b style="color:#e2e8f0">Offenses to stream against:</b> '
            + ", ".join(weak_offenses)
            + " — these teams gave up the most fantasy production to opposing "
              "defenses' schedules this season.</div>",
            unsafe_allow_html=True,
        )
    st.caption(
        "Streaming logic: pair a high-pressure defense with a soft opposing "
        "offense. Sacks and takeaways drive most DST scoring."
    )
