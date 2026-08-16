"""Reusable visual components and styling for the fantasy football app.

Every page calls inject_custom_css() first, then builds its layout from the
helpers here so the look stays consistent across pages.
"""

import streamlit as st

# Position colors matching FantasyPros conventions
POSITION_COLORS = {
    "QB": "#e74c3c",    # red
    "RB": "#2ecc71",    # green
    "WR": "#3498db",    # blue
    "TE": "#f39c12",    # orange
    "K": "#9b59b6",     # purple
    "DEF": "#95a5a6",   # gray
    "DST": "#95a5a6",
}

# Shared Plotly styling so every chart matches the dark theme
PLOTLY_TEMPLATE = "plotly_dark"
CHART_BG = "rgba(0,0,0,0)"
GRID_COLOR = "#1e293b"
ACCENT = "#3b82f6"


def style_fig(fig, height: int = 360, showlegend: bool = True):
    """Apply the app's dark chart styling to a Plotly figure."""
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        paper_bgcolor=CHART_BG,
        plot_bgcolor=CHART_BG,
        height=height,
        showlegend=showlegend,
        margin=dict(l=10, r=10, t=40, b=10),
        font=dict(color="#e2e8f0", size=12),
        legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor=GRID_COLOR),
    )
    fig.update_xaxes(gridcolor=GRID_COLOR, zerolinecolor=GRID_COLOR)
    fig.update_yaxes(gridcolor=GRID_COLOR, zerolinecolor=GRID_COLOR)
    return fig


def season_axis(fig):
    """Force whole-year ticks so seasons never render as 2,024.5."""
    fig.update_xaxes(dtick=1, tickformat="d")
    return fig


def inject_custom_css():
    """Inject custom CSS for the entire app. Call this at the top of every page.

    The stylesheet is de-indented before injection — Markdown would otherwise
    read the 4-space-indented <style> block as a code block and print the CSS
    on the page instead of applying it.
    """
    st.markdown(clean_html("""
    <style>
    /* Global overrides */
    .stApp {
        background-color: #0a0e17;
    }

    /* Remove default Streamlit padding */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }

    /* Custom card styling */
    .player-card {
        background: linear-gradient(145deg, #111827, #1a2235);
        border: 1px solid #1e293b;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 12px;
        transition: border-color 0.2s;
    }
    .player-card:hover {
        border-color: #3b82f6;
    }

    /* Position badge */
    .pos-badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 700;
        color: white;
        margin-right: 8px;
    }

    /* Recommendation badges */
    .rec-badge {
        display: inline-block;
        padding: 4px 16px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .rec-start { background: rgba(46, 204, 113, 0.2); color: #2ecc71; border: 1px solid rgba(46, 204, 113, 0.3); }
    .rec-sit { background: rgba(231, 76, 60, 0.2); color: #e74c3c; border: 1px solid rgba(231, 76, 60, 0.3); }
    .rec-flex { background: rgba(241, 196, 15, 0.2); color: #f1c40f; border: 1px solid rgba(241, 196, 15, 0.3); }
    .rec-pickup { background: rgba(52, 152, 219, 0.2); color: #3498db; border: 1px solid rgba(52, 152, 219, 0.3); }

    /* Matchup rating colors */
    .matchup-smash { color: #2ecc71; font-weight: 700; }
    .matchup-favorable { color: #82e0aa; }
    .matchup-neutral { color: #aab7b8; }
    .matchup-tough { color: #f5b041; }
    .matchup-avoid { color: #e74c3c; font-weight: 700; }

    /* Stat highlight */
    .stat-up { color: #2ecc71; }
    .stat-down { color: #e74c3c; }
    .stat-neutral { color: #aab7b8; }

    /* Section headers */
    .section-header {
        font-size: 1.3rem;
        font-weight: 700;
        color: #e2e8f0;
        margin-bottom: 16px;
        padding-bottom: 8px;
        border-bottom: 2px solid #1e293b;
    }

    /* Metric cards row */
    .metric-card {
        background: #111827;
        border: 1px solid #1e293b;
        border-radius: 10px;
        padding: 16px;
        text-align: center;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 800;
        color: #f1f5f9;
    }
    .metric-label {
        font-size: 0.75rem;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-top: 4px;
    }

    /* Navigation cards on the home page */
    .nav-card {
        background: linear-gradient(145deg, #111827, #1a2235);
        border: 1px solid #1e293b;
        border-radius: 12px;
        padding: 22px;
        height: 100%;
        min-height: 190px;
    }
    .nav-card-title {
        font-size: 1.1rem;
        font-weight: 700;
        color: #f1f5f9;
        margin-bottom: 6px;
    }
    .nav-card-q {
        font-size: 0.85rem;
        color: #3b82f6;
        font-style: italic;
        margin-bottom: 10px;
    }
    .nav-card-body {
        font-size: 0.85rem;
        color: #94a3b8;
        line-height: 1.5;
    }

    /* Verdict panel */
    .verdict {
        background: #111827;
        border-left: 4px solid #3b82f6;
        border-radius: 8px;
        padding: 16px 20px;
        margin-top: 12px;
        color: #cbd5e1;
        font-size: 0.92rem;
        line-height: 1.6;
    }

    /* Table styling */
    .dataframe { font-size: 0.85rem !important; }

    /* Hide Streamlit menu and footer */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 8px 20px;
    }
    </style>
    """), unsafe_allow_html=True)


def clean_html(html_str: str) -> str:
    """Strip per-line indentation from an HTML block.

    Markdown treats any line indented 4+ spaces as a code block, so HTML
    written inside an indented triple-quoted string renders as visible tags
    even with unsafe_allow_html=True. Removing the leading whitespace on every
    line is what actually makes it render. Safe here because none of our markup
    is whitespace-sensitive (no <pre> or <code> blocks).
    """
    return "\n".join(line.lstrip() for line in html_str.strip().splitlines())


def render(html_str: str):
    """Render an HTML block as markup, indentation-safe."""
    st.markdown(clean_html(html_str), unsafe_allow_html=True)


def position_badge(position: str) -> str:
    """Return HTML for a colored position badge."""
    color = POSITION_COLORS.get(position, "#95a5a6")
    return f'<span class="pos-badge" style="background:{color}">{position}</span>'


def recommendation_badge(rec: str) -> str:
    """Return HTML for a start/sit/pickup recommendation badge."""
    css_class = {
        "start": "rec-start",
        "sit": "rec-sit",
        "flex": "rec-flex",
        "pickup": "rec-pickup",
    }.get(rec.lower(), "rec-flex")
    return f'<span class="rec-badge {css_class}">{rec}</span>'


def matchup_rating_label(rating: float) -> str:
    """Return colored matchup label based on rating value."""
    if rating > 2:
        return '<span class="matchup-smash">🟢 Smash</span>'
    elif rating > 0.5:
        return '<span class="matchup-favorable">🟢 Favorable</span>'
    elif rating > -0.5:
        return '<span class="matchup-neutral">⚪ Neutral</span>'
    elif rating > -2:
        return '<span class="matchup-tough">🟡 Tough</span>'
    else:
        return '<span class="matchup-avoid">🔴 Avoid</span>'


def metric_card(value: str, label: str) -> str:
    """Return HTML for a single metric card."""
    return clean_html(f"""
    <div class="metric-card">
        <div class="metric-value">{value}</div>
        <div class="metric-label">{label}</div>
    </div>
    """)


def player_card_html(name: str, position: str, team: str, projected_ppg: float,
                     rank: int, rec: str = None, extra_stats: dict = None) -> str:
    """Return HTML for a player recommendation card."""
    badge = position_badge(position)
    rec_html = f' {recommendation_badge(rec)}' if rec else ''

    stats_html = ""
    if extra_stats:
        stats_items = " · ".join([
            f'<span style="color:#94a3b8">{k}:</span> <span style="color:#e2e8f0">{v}</span>'
            for k, v in extra_stats.items()
        ])
        stats_html = f'<div style="margin-top:8px;font-size:0.85rem">{stats_items}</div>'

    return clean_html(f"""
    <div class="player-card">
        <div style="display:flex;justify-content:space-between;align-items:center">
            <div>
                <span style="color:#64748b;font-size:0.8rem;margin-right:8px">#{rank}</span>
                {badge}
                <span style="font-size:1.1rem;font-weight:600;color:#f1f5f9">{name}</span>
                <span style="color:#64748b;margin-left:8px">{team}</span>
                {rec_html}
            </div>
            <div style="text-align:right">
                <span style="font-size:1.3rem;font-weight:700;color:#3b82f6">{projected_ppg:.1f}</span>
                <span style="color:#64748b;font-size:0.75rem"> PPG</span>
            </div>
        </div>
        {stats_html}
    </div>
    """)


def section_header(text: str):
    """Render a styled section header."""
    st.markdown(f'<div class="section-header">{text}</div>', unsafe_allow_html=True)


def verdict(text: str):
    """Render a verdict / reasoning panel."""
    st.markdown(f'<div class="verdict">{text}</div>', unsafe_allow_html=True)


def metric_row(items: list[tuple[str, str]]):
    """Render a row of metric cards from a list of (value, label) pairs."""
    cols = st.columns(len(items))
    for col, (value, label) in zip(cols, items):
        with col:
            st.markdown(metric_card(value, label), unsafe_allow_html=True)


# --- Shared sidebar -------------------------------------------------------

PAGE_GUIDE = [
    ("Draft War Room", "Who do I draft?"),
    ("Start/Sit Advisor", "Who do I start?"),
    ("Waiver Wire", "Who do I pick up?"),
    ("Player Intel", "How good is this player?"),
    ("AI Analyst", "Just ask a question."),
]

SCORING_LABELS = {"ppr": "PPR", "half_ppr": "Half-PPR", "standard": "Standard"}


def sidebar(season_options: list[int] = None, default_season: int = None,
            show_season: bool = True) -> tuple[str, int | None]:
    """Render the shared sidebar. Returns (scoring, season)."""
    with st.sidebar:
        st.markdown(
            '<div style="font-size:1.05rem;font-weight:700;color:#f1f5f9;'
            'letter-spacing:0.02em">🏈 Fantasy Football Analytics</div>'
            '<div style="color:#64748b;font-size:0.78rem;margin-bottom:18px">'
            'nflverse + Pro Football Reference</div>',
            unsafe_allow_html=True,
        )

        scoring = st.selectbox(
            "Scoring format",
            ["ppr", "half_ppr", "standard"],
            index=0,
            format_func=lambda s: SCORING_LABELS[s],
            key="scoring_format",
        )

        season = None
        if show_season:
            opts = season_options or [2025, 2024, 2023, 2022, 2021]
            idx = opts.index(default_season) if default_season in opts else 0
            season = st.selectbox("Season", opts, index=idx, key="season_select")

        st.markdown("---")
        st.markdown(
            '<div style="color:#64748b;font-size:0.72rem;text-transform:uppercase;'
            'letter-spacing:0.08em;margin-bottom:8px">Pages</div>',
            unsafe_allow_html=True,
        )
        for title, question in PAGE_GUIDE:
            st.markdown(
                f'<div style="margin-bottom:7px;line-height:1.3">'
                f'<span style="color:#e2e8f0;font-size:0.82rem">{title}</span><br>'
                f'<span style="color:#64748b;font-size:0.74rem">{question}</span></div>',
                unsafe_allow_html=True,
            )

    return scoring, season


def api_guard(data, what: str) -> bool:
    """Show a friendly message and return False when an API call came back empty."""
    if not data:
        st.warning(
            f"No {what} available right now. The API may be unreachable or the "
            f"selected season may have no data yet."
        )
        return False
    return True
