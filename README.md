# Fantasy Football Analytics Platform

A data engineering and analytics project that ingests free NFL/fantasy football data, models it in SQL Server, and surfaces insights through Power BI.

## Architecture

```
nflverse (free data)  →  Python (ingest)  →  SQL Server  →  Power BI
```

### Data Layers

| Schema      | Purpose                                    |
|-------------|-------------------------------------------|
| `raw`       | Landed source data, minimal transformation |
| `staging`   | Cleaned and standardized                   |
| `warehouse` | Dimensional model (dims + facts)           |
| `mart`      | Power BI-ready views and aggregations      |

### Core Model

The warehouse is modeled at **player-week grain** to support weekly fantasy decision-making.

- **Fantasy points are calculated, not stored.** Raw stat components live in `fact_player_week`; fantasy scoring is computed in mart views using `dim_scoring_format`, supporting Standard, Half-PPR, and PPR formats.

## Data Sources

All version 1 data comes from the free [nflverse](https://github.com/nflverse) ecosystem via [nflreadpy](https://nflreadpy.nflverse.com/).

| Dataset         | Function                    |
|-----------------|-----------------------------|
| Player stats    | `load_player_stats()`       |
| Schedules       | `load_schedules()`          |
| Players         | `load_players()`            |
| Weekly rosters  | `load_rosters_weekly()`     |

## Tech Stack

- **Python 3.12** — ingestion and loading
- **SQL Server** (Docker) — warehouse
- **Power BI** — reporting
- **nflreadpy** — data source package

## Setup

### Prerequisites

- Python 3.12
- SQL Server instance (Docker recommended)
- ODBC Driver 18 for SQL Server
- Power BI Desktop

### Installation

```bash
# Clone the repo
git clone https://github.com/GitHamzah/fantasy-football-analytics.git
cd fantasy-football-analytics

# Create virtual environment
py -3.12 -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Configure connection
cp config/config.template.yaml config/config.yaml
# Edit config/config.yaml with your SQL Server details
```

### Database Setup

Run the SQL scripts in order against your `FantasyFootball` database:

1. `sql/schemas/01_create_schemas.sql`
2. `sql/warehouse/01_dim_tables.sql`
3. `sql/warehouse/02_fact_player_week.sql`
4. `sql/warehouse/03_seed_reference_data.sql`
5. `sql/mart/01_vw_player_week_fantasy.sql`

### Run Ingestion

```bash
# Ingest all configured seasons
python run_ingest.py

# Ingest specific seasons
python run_ingest.py --seasons 2023 2024
```

## Project Status

- [x] Project structure and config
- [x] Raw layer ingestion (player stats, schedules, players, rosters)
- [x] Warehouse dimensional model
- [x] Mart views with multi-format fantasy scoring
- [ ] Warehouse transformation scripts (raw → warehouse)
- [ ] Power BI reports
- [ ] Phase 2: Fantasy enrichments (rankings, expected points, player IDs)
- [ ] Phase 3: Usage context (snap counts, depth charts)

## License

Personal project — not affiliated with the NFL or nflverse.
