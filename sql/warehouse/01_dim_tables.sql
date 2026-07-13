-- ============================================
-- Warehouse dimension tables
-- ============================================

-- dim_player: One row per player in the nflverse universe.
-- Source: raw.players
IF OBJECT_ID('warehouse.dim_player', 'U') IS NULL
CREATE TABLE warehouse.dim_player (
    player_key          INT IDENTITY(1,1) PRIMARY KEY,
    gsis_id             VARCHAR(50)     NOT NULL,   -- nflverse primary key
    display_name        VARCHAR(150)    NULL,
    first_name          VARCHAR(100)    NULL,
    last_name           VARCHAR(100)    NULL,
    position            VARCHAR(10)     NULL,
    position_group      VARCHAR(20)     NULL,
    height              INT             NULL,       -- inches
    weight              INT             NULL,       -- pounds
    birth_date          DATE            NULL,
    college             VARCHAR(100)    NULL,
    draft_year          INT             NULL,
    draft_round         INT             NULL,
    draft_pick          INT             NULL,
    entry_year          INT             NULL,
    rookie_year         INT             NULL,
    status              VARCHAR(30)     NULL,
    loaded_at           DATETIME2       NOT NULL DEFAULT SYSUTCDATETIME(),

    CONSTRAINT uq_dim_player_gsis UNIQUE (gsis_id)
);
GO

-- dim_team: One row per team abbreviation.
-- Manually seeded or derived from source data.
IF OBJECT_ID('warehouse.dim_team', 'U') IS NULL
CREATE TABLE warehouse.dim_team (
    team_key            INT IDENTITY(1,1) PRIMARY KEY,
    team_abbr           VARCHAR(5)      NOT NULL,
    team_name           VARCHAR(100)    NULL,
    team_conference     VARCHAR(5)      NULL,       -- AFC / NFC
    team_division       VARCHAR(20)     NULL,       -- e.g. NFC East
    loaded_at           DATETIME2       NOT NULL DEFAULT SYSUTCDATETIME(),

    CONSTRAINT uq_dim_team_abbr UNIQUE (team_abbr)
);
GO

-- dim_week: One row per season-week combination.
-- Source: derived from raw.schedules distinct season/week.
IF OBJECT_ID('warehouse.dim_week', 'U') IS NULL
CREATE TABLE warehouse.dim_week (
    week_key            INT IDENTITY(1,1) PRIMARY KEY,
    season              INT             NOT NULL,
    week                INT             NOT NULL,
    season_type         VARCHAR(10)     NULL,       -- REG, POST
    loaded_at           DATETIME2       NOT NULL DEFAULT SYSUTCDATETIME(),

    CONSTRAINT uq_dim_week UNIQUE (season, week)
);
GO

-- dim_game: One row per NFL game.
-- Source: raw.schedules
IF OBJECT_ID('warehouse.dim_game', 'U') IS NULL
CREATE TABLE warehouse.dim_game (
    game_key            INT IDENTITY(1,1) PRIMARY KEY,
    game_id             VARCHAR(30)     NOT NULL,   -- nflverse game_id
    season              INT             NOT NULL,
    week                INT             NOT NULL,
    game_type           VARCHAR(10)     NULL,
    gameday             DATE            NULL,
    gametime            VARCHAR(10)     NULL,
    home_team           VARCHAR(5)      NULL,
    away_team           VARCHAR(5)      NULL,
    home_score          INT             NULL,
    away_score          INT             NULL,
    spread_line         DECIMAL(5,1)    NULL,
    total_line          DECIMAL(5,1)    NULL,
    stadium             VARCHAR(100)    NULL,
    roof                VARCHAR(20)     NULL,
    surface             VARCHAR(30)     NULL,
    loaded_at           DATETIME2       NOT NULL DEFAULT SYSUTCDATETIME(),

    CONSTRAINT uq_dim_game_id UNIQUE (game_id)
);
GO

-- dim_position: Static reference table for position metadata.
IF OBJECT_ID('warehouse.dim_position', 'U') IS NULL
CREATE TABLE warehouse.dim_position (
    position_key        INT IDENTITY(1,1) PRIMARY KEY,
    position_abbr       VARCHAR(10)     NOT NULL,
    position_name       VARCHAR(50)     NULL,
    position_group      VARCHAR(20)     NULL,       -- QB, RB, WR, TE, K, DEF
    is_fantasy_relevant BIT             NOT NULL DEFAULT 1,
    loaded_at           DATETIME2       NOT NULL DEFAULT SYSUTCDATETIME(),

    CONSTRAINT uq_dim_position_abbr UNIQUE (position_abbr)
);
GO

-- dim_scoring_format: Reference table for fantasy scoring systems.
IF OBJECT_ID('warehouse.dim_scoring_format', 'U') IS NULL
CREATE TABLE warehouse.dim_scoring_format (
    scoring_format_key  INT IDENTITY(1,1) PRIMARY KEY,
    format_name         VARCHAR(20)     NOT NULL,   -- Standard, Half-PPR, PPR
    pts_per_reception   DECIMAL(4,2)    NOT NULL,   -- 0, 0.5, 1.0
    pts_passing_yard    DECIMAL(6,4)    NOT NULL DEFAULT 0.04,
    pts_passing_td      DECIMAL(4,1)    NOT NULL DEFAULT 4.0,
    pts_interception    DECIMAL(4,1)    NOT NULL DEFAULT -2.0,
    pts_rushing_yard    DECIMAL(6,4)    NOT NULL DEFAULT 0.1,
    pts_rushing_td      DECIMAL(4,1)    NOT NULL DEFAULT 6.0,
    pts_receiving_yard  DECIMAL(6,4)    NOT NULL DEFAULT 0.1,
    pts_receiving_td    DECIMAL(4,1)    NOT NULL DEFAULT 6.0,
    pts_fumble_lost     DECIMAL(4,1)    NOT NULL DEFAULT -2.0,
    pts_2pt_conversion  DECIMAL(4,1)    NOT NULL DEFAULT 2.0,
    loaded_at           DATETIME2       NOT NULL DEFAULT SYSUTCDATETIME(),

    CONSTRAINT uq_dim_scoring_format UNIQUE (format_name)
);
GO
