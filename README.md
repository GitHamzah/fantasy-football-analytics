# 🏈 Fantasy Football Analytics Platform

A full-stack data engineering and analytics platform that ingests NFL data, models it through a layered SQL Server warehouse, and serves fantasy football insights through a FastAPI backend, Streamlit web application, and Power BI semantic model.

**[Live App](https://ff-analytics.streamlit.app)** · **[API Docs](https://fantasy-football-api-34ko.onrender.com/docs)** · **[Portfolio](https://githamzah.github.io)**

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         DATA SOURCES                                │
│                    nflverse / nflreadpy (free)                       │
│         player stats · schedules · rosters · snap counts            │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                     Python Ingestion
                             │
┌────────────────────────────▼────────────────────────────────────────┐
│                     SQL SERVER (Docker/NAS)                          │
│                                                                     │
│   raw          │  staging        │  warehouse       │  mart          │
│   landed       │  cleaned &      │  dim_player      │  dim_player    │
│   source data  │  standardized   │  dim_team        │  dim_team      │
│                │                 │  dim_week        │  dim_week      │
│                │                 │  dim_game        │  dim_game      │
│                │                 │  fact_player_week│  fact_player_  │
│                │                 │                  │    week        │
│                │                 │                  │  dim_scoring_  │
│                │                 │                  │    format      │
│                │                 │                  │                │
│   Python       │  ◄── dbt ──►   │  ◄── dbt ──►    │  ◄── dbt ──►  │
│   loads here   │  transforms     │  models          │  serves        │
└────────────────┴────────────────┴──────────────────┴────────────────┘
                             │                                │
                      sync_to_neon.py                         │
                             │                                │
                    ┌────────▼────────┐                       │
                    │  Neon Postgres   │                       │
                    │  (production)    │                       │
                    └────────┬────────┘                       │
                             │                                │
                    ┌────────▼────────┐              ┌────────▼────────┐
                    │    FastAPI       │              │    Power BI      │
                    │  14 endpoints    │              │  Star schema     │
                    │  + Gemini AI     │              │  DAX measures    │
                    │  (Render)        │              │  Disconnected    │
                    └────────┬────────┘              │  scoring format  │
                             │                       └─────────────────┘
                    ┌────────▼────────┐
                    │   Streamlit      │
                    │  7 pages         │
                    │  (Streamlit      │
                    │   Cloud)         │
                    └─────────────────┘
```

## Features

### Analytics
- **Player Projections** — weighted historical averages (60/30/10 across 3 seasons), age curve adjustments, and availability projections for upcoming season
- **Value Over Replacement (VOR)** — positional scarcity-adjusted rankings for draft strategy
- **Consistency Analysis** — boom/bust rates, floor/ceiling, and consistency scoring (PPG/StdDev)
- **Opportunity vs Production** — scatter analysis identifying buy-low and sell-high candidates via target share, carries, and WOPR
- **Schedule Difficulty** — team schedule strength ratings by position based on prior season defensive rankings, with week-by-week matchup previews
- **Career Trajectories** — multi-season PPG and opportunity trends per player
- **Sit/Start Comparisons** — head-to-head player analysis with floor, ceiling, consistency, recent trend, and weekly overlay charts

### AI Assistant
- Natural language Q&A powered by Google Gemini
- Grounded in actual database stats — the AI retrieves relevant data before answering
- Season-aware context detection (asking about 2024 pulls 2024 data)
- Supports player lookups, waiver wire analysis, and trending player queries

### Scoring Formats
- Standard, Half-PPR, and PPR all supported
- Fantasy points calculated dynamically, not stored — raw stat components in the warehouse, scoring logic in DAX (Power BI) and SQL (API)

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Data Source | [nflverse](https://github.com/nflverse) / nflreadpy | Free NFL data (player stats, schedules, rosters) |
| Ingestion | Python, pandas | Extract and load to SQL Server |
| Database (dev) | SQL Server (Docker) | Data warehouse on NAS |
| Database (prod) | Neon Postgres | Cloud database for public deployment |
| Transformation | dbt Core + dbt-sqlserver | Staging → warehouse → mart with tests and docs |
| API | FastAPI | REST endpoints for stats, analytics, projections, AI |
| Frontend | Streamlit | Interactive web application |
| BI | Power BI | Star schema, DAX measures, reports |
| AI | Google Gemini API | Natural language analytics assistant |
| Hosting | Render (API), Streamlit Cloud (frontend) | Auto-deploy on git push |

## Data

- **5 seasons** of NFL data (2021–2025)
- **94,000+** player-week stat records
- **25,000+** players in the universe
- **1,600+** games with scores and metadata
- **2026 schedule** loaded for draft prep projections
- **56/56** dbt tests passing

All data sourced from the free [nflverse](https://github.com/nflverse) ecosystem.

## Project Structure

```
fantasy-football-analytics/
│
├── run_ingest.py                  # Main ingestion runner
├── sync_to_neon.py                # SQL Server → Neon data sync
├── render.yaml                    # Render deployment config
├── requirements.txt               # Python ingestion dependencies
│
├── config/
│   ├── config.template.yaml       # Database config template
│   └── config.yaml                # Local config (gitignored)
│
├── src/                           # Python ingestion pipeline
│   ├── config.py                  # YAML config loader
│   ├── db.py                      # SQL Server connection helpers
│   └── ingest/
│       ├── player_stats.py        # load_player_stats() → raw
│       ├── players.py             # load_players() → raw
│       ├── schedules.py           # load_schedules() → raw
│       └── rosters_weekly.py      # load_rosters_weekly() → raw
│
├── dbt/                           # dbt transformation project
│   ├── dbt_project.yml
│   ├── models/
│   │   ├── staging/               # Cleaned source data (views)
│   │   │   ├── stg_players.sql
│   │   │   ├── stg_player_stats.sql
│   │   │   ├── stg_schedules.sql
│   │   │   └── stg_rosters_weekly.sql
│   │   ├── warehouse/             # Dimensional model (tables)
│   │   │   ├── dim_player.sql
│   │   │   ├── dim_team.sql
│   │   │   ├── dim_week.sql
│   │   │   ├── dim_game.sql
│   │   │   └── fact_player_week.sql
│   │   └── mart/                  # Power BI / API ready (views)
│   │       ├── mart_dim_player.sql
│   │       ├── mart_dim_team.sql
│   │       ├── mart_dim_week.sql
│   │       ├── mart_dim_game.sql
│   │       ├── mart_dim_scoring_format.sql
│   │       └── mart_fact_player_week.sql
│   ├── seeds/
│   │   ├── scoring_formats.csv    # Standard, Half-PPR, PPR weights
│   │   └── positions.csv          # Position reference data
│   └── tests/
│
├── api/                           # FastAPI backend
│   ├── main.py                    # App entry point
│   ├── config.py                  # Environment-based settings
│   ├── database.py                # DB connection (SQL Server + Postgres)
│   ├── routers/
│   │   ├── players.py             # Player search and lookup
│   │   ├── stats.py               # Season and weekly stats
│   │   ├── leaders.py             # Fantasy leaderboards
│   │   ├── analytics.py           # Consistency, VOR, opportunity, defense
│   │   ├── projections.py         # Player projections and schedule strength
│   │   └── ai.py                  # Gemini-powered Q&A
│   ├── services/
│   │   ├── ai.py                  # AI data retrieval + Gemini integration
│   │   └── projections.py         # Projection engine
│   └── models/
│       └── __init__.py            # Pydantic response models
│
└── streamlit/                     # Streamlit frontend
    ├── app.py                     # Home page
    ├── .streamlit/config.toml     # Theme config
    ├── utils/api.py               # API client with caching
    └── pages/
        ├── 0_Draft_Prep_2026.py   # Projections, schedule, draft cards
        ├── 1_Dashboard.py         # Leaders, VOR, consistency
        ├── 2_Player_Lookup.py     # Search, compare, trajectory
        ├── 3_Matchups_Opportunity.py  # Defense rankings, opportunity scatter
        ├── 4_Draft_Board.py       # VOR rankings, season comparison
        ├── 5_Sit_Start.py         # Head-to-head player comparison
        └── 6_AI_Assistant.py      # Chat with Gemini about the data
```

## Setup

### Prerequisites

- Python 3.12
- SQL Server instance (Docker recommended)
- ODBC Driver 18 for SQL Server
- Power BI Desktop (optional, for BI layer)

### Local Development

```bash
# Clone
git clone https://github.com/GitHamzah/fantasy-football-analytics.git
cd fantasy-football-analytics

# Virtual environment
py -3.12 -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/Mac

# Install dependencies
pip install -r requirements.txt
pip install -r api/requirements.txt

# Configure database connection
cp config/config.template.yaml config/config.yaml
# Edit config/config.yaml with your SQL Server details

# Configure API
cp api/.env.example api/.env
# Edit api/.env with your database and Gemini API credentials
```

### Database Setup

Run the SQL schema script against your `FantasyFootball` database:

```sql
CREATE DATABASE FantasyFootball;
```

### Ingest Data

```bash
python run_ingest.py --seasons 2021 2022 2023 2024 2025 2026
```

### Run dbt

```bash
cd dbt
dbt build
```

All 56 tests should pass with 2 expected warnings (null player IDs in source data, filtered in staging).

### Run API

```bash
cd api
uvicorn main:app --reload
# Open http://localhost:8000/docs
```

### Run Streamlit

In a second terminal:

```bash
cd streamlit
streamlit run app.py
# Open http://localhost:8501
```

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/players/search?q=Lamar` | Search players by name |
| GET | `/players/fantasy-relevant` | All fantasy-relevant players (for dropdowns) |
| GET | `/players/{id}` | Player detail |
| GET | `/stats/season/{id}` | Aggregated season stats |
| GET | `/stats/weekly/{id}?season=2024` | Week-by-week stats |
| GET | `/leaders/season?season=2024` | Season fantasy leaders |
| GET | `/leaders/weekly?season=2024&week=1` | Weekly fantasy leaders |
| GET | `/analytics/consistency?season=2024` | Consistency rankings with boom/bust |
| GET | `/analytics/vor?season=2024` | Value Over Replacement rankings |
| GET | `/analytics/opportunity?season=2024` | Opportunity vs production data |
| GET | `/analytics/defense?season=2024` | Defensive matchup rankings |
| GET | `/analytics/trajectory/{id}` | Multi-season career trajectory |
| GET | `/analytics/compare?player_ids=id1,id2&season=2024` | Head-to-head comparison |
| GET | `/projections/players?season=2026` | Player projections for target season |
| GET | `/projections/schedule?season=2026` | Schedule difficulty by team/position |
| GET | `/projections/schedule/{team}?season=2026` | Team week-by-week matchup ratings |
| POST | `/ai/ask` | Natural language question → AI answer |

All stat endpoints support `scoring` parameter: `standard`, `half_ppr`, `ppr`.

## Data Model

### Design Principles

- **Player-week grain** — the central analytical unit for fantasy football
- **Raw stat components stored, not fantasy points** — scoring logic calculated in the semantic layer (DAX) and API, not baked into the warehouse
- **Disconnected scoring dimension** — Power BI uses a slicer-driven DAX measure to calculate fantasy points dynamically across Standard, Half-PPR, and PPR
- **All lowercase snake_case** in the database — Title Case applied only in the Power BI semantic layer via SQL aliases in Power Query
- **Layered architecture** — raw (land it), staging (clean it), warehouse (model it), mart (serve it)

### Warehouse Layers

| Schema | Purpose | Managed By |
|---|---|---|
| `raw` | Landed source data, no transformation | Python ingestion |
| `staging` | Cleaned, typed, standardized | dbt (views) |
| `warehouse` | Dimensional model — dims and facts | dbt (tables) |
| `mart` | Consumption-ready for Power BI and API | dbt (views) |

## Projection Methodology

The projection engine generates fantasy projections for upcoming seasons using:

1. **Weighted PPG** — 60% most recent season, 30% prior, 10% two years back
2. **Age Curve** — position-specific multipliers (RBs decline after 27, QBs stable through 35, WRs peak 24–30, TEs peak 25–31)
3. **Availability** — projected games based on historical games played average
4. **Season Total** — adjusted PPG × projected games
5. **Schedule Difficulty** — prior season defensive rankings mapped to target season schedule

## Deployment

| Service | Platform | Trigger |
|---|---|---|
| FastAPI | Render (free tier) | Auto-deploy on git push |
| Streamlit | Streamlit Cloud (free) | Auto-deploy on git push |
| Database | Neon Postgres (free) | Manual sync via `sync_to_neon.py` |

### Sync Data to Production

```bash
$env:NEON_DATABASE_URL = "your_neon_connection_string"
python sync_to_neon.py
```

## Future Roadmap

- [ ] Sleeper API integration for league-specific analytics
- [ ] Authentication and tiered access (public analytics vs league data)
- [ ] ETL audit timestamps and refresh logging
- [ ] Self-hosted deployment via Cloudflare Tunnel
- [ ] Snap count and depth chart integration
- [ ] Power BI report pages
- [ ] Decision-oriented dashboard redesign
- [ ] Waiver wire recommendation engine

## License

Personal project — not affiliated with the NFL or nflverse.
