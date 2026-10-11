# Fantasy Football Analytics Platform - Handoff Context Document

## Last Updated: October 2026

## Project Owner
Hamzah Lydick (Doinworqson on Sleeper)
- Senior BI professional, DFW (Carrollton, TX)
- U.S. Army Veteran
- M.S. Business Analytics (East Texas A&M), B.S. Accounting (UT Dallas)
- LinkedIn: https://www.linkedin.com/in/hamzahlydick/
- GitHub: https://github.com/GitHamzah

## Live Deployments

| Service | URL | Platform | Auto-deploys |
|---|---|---|---|
| React Frontend | https://fantasy-football-app-ten.vercel.app | Vercel | On push to main |
| API Backend | https://fantasy-football-api-34ko.onrender.com | Render (free tier) | On push to master |
| API Docs | https://fantasy-football-api-34ko.onrender.com/docs | Swagger/OpenAPI | With API |
| Streamlit App | https://ff-analytics.streamlit.app | Streamlit Cloud | On push |
| Portfolio | https://githamzah.github.io | GitHub Pages | On push to main |

UptimeRobot pings the Render API every 5 minutes to prevent cold starts.

## GitHub Repos

| Repo | Purpose |
|---|---|
| GitHamzah/fantasy-football-analytics | Main project: ingestion, dbt, API, ML, Streamlit |
| GitHamzah/fantasy-football-app | React/Next.js frontend |
| GitHamzah/GitHamzah.github.io | Portfolio website |

## Architecture

```
nflverse + PFR + Sleeper API
    -> Python ingestion (src/ingest/)
    -> SQL Server (Docker on NAS, db: FantasyFootball)
    -> dbt Core (staging views -> warehouse tables -> mart views/tables)
    -> sync_to_neon.py -> Neon Postgres (production DB for API)
    -> FastAPI (Render)
    -> React/Next.js (Vercel)
    -> Streamlit (Streamlit Cloud)
    -> Power BI (local, connects to SQL Server)
```

## Database Connections

**SQL Server (local/development):**
- Host: 192.168.1.119:1433
- Database: FantasyFootball
- User: sa
- Config: config/config.yaml (gitignored)

**Neon Postgres (production):**
- Connection string stored in environment variable NEON_DATABASE_URL
- Set via: $env:NEON_DATABASE_URL in PowerShell
- Tables are in public schema (no mart. prefix)
- Obtain the connection string from https://console.neon.tech project settings
- NEVER commit this value to the repo

**Render env vars:**
- DATABASE_URL (Neon connection string)
- GEMINI_API_KEY
- GEMINI_MODEL
- APP_ENV=production

## Database Schema

### Raw Layer (SQL Server only: raw.*)
| Table | Rows | Source |
|---|---|---|
| raw.player_stats | 94,738 | nflreadpy.load_player_stats() |
| raw.players | 25,066 | nflreadpy.load_players() |
| raw.schedules | ~1,696 | nflreadpy.load_schedules() |
| raw.rosters_weekly | ~150K | nflreadpy.load_rosters_weekly() |
| raw.pfr_pass | 3,472 | nflreadpy.load_pfr_advstats(stat_type='pass') |
| raw.pfr_rush | 11,858 | nflreadpy.load_pfr_advstats(stat_type='rush') |
| raw.pfr_rec | 22,735 | nflreadpy.load_pfr_advstats(stat_type='rec') |
| raw.pfr_def | 40,140 | nflreadpy.load_pfr_advstats(stat_type='def') |
| raw.participation | 238,135 | nflreadpy.load_participation() |
| raw.pbp | 176,478 | nflreadpy.load_pbp() (pass/run only) |

### Sleeper Schema (SQL Server only: sleeper.*)
| Table | Rows | Source |
|---|---|---|
| sleeper.league | 12 | Sleeper API /user/{id}/leagues |
| sleeper.user | 122 | Sleeper API /league/{id}/users |
| sleeper.roster | 126 | Sleeper API /league/{id}/rosters |
| sleeper.roster_player | 1,345 | Normalized from roster.players |
| sleeper.matchup | 1,636 | Sleeper API /league/{id}/matchups/{week} |
| sleeper.draft_pick | 1,328 | Sleeper API /draft/{id}/picks |
| sleeper.transaction | 2,522 | Sleeper API /league/{id}/transactions/{week} |
| sleeper.player_map | 9,442 | Sleeper API /players/nfl + nflverse crosswalk |

Note: sleeper.[user] and sleeper.[transaction] are reserved SQL words - use brackets in T-SQL.

### Staging Layer (dbt views)
- stg_player_stats, stg_players, stg_schedules, stg_rosters_weekly
- stg_pfr_pass, stg_pfr_rush, stg_pfr_rec, stg_pfr_def
- stg_participation (with offense/defense personnel parsers + coverage_shell)
- stg_pbp
- stg_sleeper_roster, stg_sleeper_matchup, stg_sleeper_draft

### Warehouse Layer (dbt tables)
- dim_player, dim_team, dim_week, dim_game, dim_scoring_format
- fact_player_week (with 14 defensive columns)
- fact_pfr_advstats (unified 4 PFR types, 68,167 rows)
- fact_formation (team-season-formation-personnel grain, 3,492 rows)
- fact_def_formation (team-season-def_package-shell grain)
- fact_play_matchup (pbp joined with participation, 176,478 rows)

### Mart Layer (synced to Neon)
| Mart Table | Neon Table | Rows | Description |
|---|---|---|---|
| mart.dim_player | dim_player | 25,066 | Player dimension |
| mart.dim_team | dim_team | 32 | Team dimension |
| mart.dim_week | dim_week | 110 | Week dimension |
| mart.dim_game | dim_game | 1,424+ | Game/schedule dimension |
| mart.dim_scoring_format | dim_scoring_format | 3 | PPR/Half/Standard |
| mart.fact_player_week | fact_player_week | 94,738 | Core fantasy stats |
| mart.team_defense | team_defense | 160 | Team defensive stats |
| mart.pfr_advstats | pfr_advstats | 68,167 | PFR advanced stats |
| mart.formation | formation | 3,492 | Offensive formation tendencies |
| mart.def_formation | def_formation | 528+ | Defensive formation tendencies |
| mart.player_vs_defense | player_vs_defense | 87,198 | Player splits by defensive look |
| mart.team_matchup | team_matchup | 17,719 | Team vs team by scheme |
| mart.schedule_projection | schedule_projection | 6,528 | Weekly scheme-adjusted projections |
| mart.season_projection | season_projection | 384 | Season rollup projections |
| mart.my_roster | my_roster | 31 | Hamzah's Sleeper rosters + analytics |
| mart.league_standings | league_standings | 65+ | All league standings |
| mart.league_matchup | league_matchup | 1,636 | Weekly league matchups |

## dbt

- **Total nodes:** 89+
- **dbt executable:** AppData\Local\Python\pythoncore-3.14-64\Scripts\dbt.exe (dbt-core 1.12.3, NOT dbt-fusion)
- **Profiles:** C:\Users\HLydi\.dbt\profiles.yml
- **Build command:** cd dbt && dbt build

## ML Model

- **Algorithm:** GradientBoostingRegressor (scikit-learn)
- **MAE:** 2.56 fantasy PPG
- **R-squared:** 0.67
- **Features:** 26 (top: total_yards_pg 37%, ppg 34%)
- **Training:** 2021-2023 seasons, validated on 2024 predicting 2025
- **PFR features included:** 95.1% bridge match rate
- **Model file:** api/models/projection_model.joblib (337KB, committed to repo)
- **Fallback:** weighted_avg for non-PPR scoring or missing model

## API Endpoints (FastAPI)

### Routers
| Router | Prefix | Endpoints |
|---|---|---|
| players | /players | search, detail, fantasy-relevant |
| stats | /stats | season/{id}, weekly/{id} |
| leaders | /leaders | season, weekly |
| analytics | /analytics | vor, consistency, opportunity, defense, compare, trajectory |
| projections | /projections | players (ML), schedule |
| schedule_projections | /projections | schedule-adjusted, weekly-matchup |
| advanced | /advanced | team-defense, pfr/player/{id}, pfr/defense-vs-position |
| formations | /advanced | formations, formations/league, formations/roster, def-formations, def-formations/league, def-formations/roster |
| matchups | /matchups | player/{id}, player/{id}/vs-team, team, top-performers |
| game_matchups | /games | week, matchup (flagship with grading), player-vs-look |
| leagues | /leagues | list, {id}/roster, {id}/standings, {id}/matchups |
| ai | /ai | ask (Gemini-powered) |

### Cross-DB Compatibility Rules
- COALESCE (never ISNULL)
- OFFSET/FETCH (never TOP)
- STDDEV translation handled in execute_query
- mart. prefix stripped automatically on Postgres via execute_query
- All numeric values cast to float/int (never Decimal) in responses

## Matchup Grading System (0-100)

**Offensive Player Grade:**
- 40%: Scheme fit (shell-weighted yards/attempt vs opponent tendencies)
- 25%: Production (2025 PPG percentile)
- 20%: Historical vs this specific defense
- 15%: Consistency (stddev + boom rate)

**Defensive Player Grade:**
- PFR metric percentiles by position bucket
- CB/S: completion% allowed, yards/target, passer rating, INTs
- DL: sacks, pressures, missed tackle%
- LB: tackles, missed tackle%, coverage stats

**Grade Labels:**
90-100: Elite, 80-89: Great, 70-79: Good, 60-69: Average, 50-59: Below Average, 40-49: Poor, 0-39: Terrible

## React Frontend (fantasy-football-app)

**Stack:** Next.js + TypeScript + Tailwind CSS
**Deploy:** Vercel, env var NEXT_PUBLIC_API_URL
**Design:** Dark theme inspired by nfl-grades.shanethakkar.com

**Pages:**
- / (Rankings) - Standard + Schedule-Adjusted toggle, position tabs
- /players (Browse/Search) - searchable player list
- /players/[slug] (Player Detail) - stats, charts, defensive splits, 2026 schedule outlook
- /matchups (Game Matchups) - flagship page with unified dual-formation field, grading, position matchups
- /formations (Team Formations) - offense/defense toggle, SVG field with real players
- /waiver-wire (Waiver Wire) - trending players
- /ai (AI Analyst) - Gemini chat with quick prompts
- /my-leagues (My Leagues) - Sleeper integration hub
- /my-leagues/[id] (League Detail) - roster with analytics, standings, matchups

**Key Components:**
- SortableTable (with auto-tooltips from KPI dictionary, numeric sort, sticky headers)
- FormationField / DefenseField / MatchupField (SVG field visualizations)
- Tooltip (KPI definitions)
- PlayerCard (clickable links to detail pages)
- TeamLogo (ESPN CDN with abbreviation remap: LA->lar, WAS->wsh, OAK->lv, JAC->jax)

## Sleeper Integration

- **Username:** Doinworqson
- **User ID:** 997944313776496640
- **Leagues:** 12 across 2023-2026, all 1.0 PPR
- **Active 2026 leagues:** Alkhawaldeh League (in_season), Fantastan Football (in_season)
- **Player ID bridge:** 92.3% GSIS match on drafted players (Sleeper gsis_id + nflverse crosswalk)
- **Refresh:** python -m src.ingest.sleeper (full replace, ~330 API calls)

## Key File Paths (Local)

- Project root: C:\Users\HLydi\OneDrive\Business Intelligence\Portfolio\Fantacy Football Portfolio Project
- React app: C:\Users\HLydi\OneDrive\Business Intelligence\Portfolio\fantasy-football-app
- Portfolio: C:\Users\HLydi\OneDrive\Business Intelligence\Portfolio\GitHamzah.github.io
- dbt profiles: C:\Users\HLydi\.dbt\profiles.yml
- API env: api/.env (gitignored)
- Python config: config/config.yaml (gitignored)

## Python Environment

- **Python version:** 3.12 (via py -3.12)
- **Venv:** .venv in project root
- **Rebuild:** py -3.12 -m venv .venv --clear && pip install -r requirements.txt && pip install -r api/requirements.txt
- **Note:** PYTHONIOENCODING=utf-8 needed if scheduling run_ingest.py (cp1252 encoding crash on special chars)

## Ingestion Pipeline

```
python run_ingest.py --seasons 2021 2022 2023 2024 2025 2026
```

7 steps:
1. Player Stats (load_player_stats)
2. Players (load_players)
3. Schedules (load_schedules)
4. Rosters Weekly (load_rosters_weekly)
5. PFR Advanced Stats (4 stat types)
6. Participation (formations/personnel)
7. Play-by-Play (pass/run only)

Sleeper is separate: `python -m src.ingest.sleeper`

## Deployment Workflow

```powershell
# 1. Build dbt
cd dbt && dbt build && cd ..

# 2. Sync to Neon (get connection string from Neon console)
$env:NEON_DATABASE_URL = "your_neon_connection_string_here"
python sync_to_neon.py

# 3. Push API (triggers Render deploy)
git add . && git commit -m "message" && git push

# 4. Push React app (triggers Vercel deploy)
cd ..\fantasy-football-app
git add . && git commit -m "message" && git push
```

## Known Issues and Gotchas

1. **OneDrive locks .git/objects/** during push - hit `n` on deletion prompts
2. **Render free tier cold starts** - UptimeRobot keeps it warm
3. **ML projections return weighted_avg for non-PPR** - model trained on PPR only
4. **Formation labels incomparable 2022 to 2023** - 7-value vs 3-value vocabulary change
5. **PFR bridge is name+team+season+week** - ~86% match, not gsis_id
6. **Sleeper player_map gsis_id** is only ~24% from Sleeper's own field - nflverse crosswalk fills the rest
7. **dim_player.current_team** only as fresh as last players ingest
8. **2026 rosters** fall back to current_team from dim_player (no game data yet)
9. **Reserved SQL words** in sleeper schema - bracket [user] and [transaction]
10. **Defense personnel parsing** changed between 2022 and 2023 - parser handles both

## Decisions Log

- All lowercase snake_case in database; Title Case only in BI semantic layer
- Fantasy points calculated dynamically, not stored
- Disconnected dim_scoring_format in Power BI for what-if scoring
- COALESCE + OFFSET/FETCH for cross-DB SQL (never ISNULL/TOP)
- ML model committed to repo (Render needs it or falls back silently)
- Separate React repo for premium frontend; Streamlit kept as prototype
- Email obfuscated via JS split on portfolio
- dbt mart models materialized as tables (not views) for Neon sync performance

## What's Next (Backlog)

- Coach tracking table for scheme-transfer projections (coaches carry schemes to new teams)
- Kicker analysis by stadium and opponent
- Power BI report screenshots for portfolio
- Weekly Sleeper refresh automation
- Trade analyzer using matchup data
- Self-hosted deployment via Cloudflare Tunnel
- Update README to reflect current state
