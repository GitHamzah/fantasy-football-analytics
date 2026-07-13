-- ============================================
-- fact_player_week: Core fact table at player-week grain.
-- Stores raw stat components. Fantasy points are NOT stored here —
-- they are calculated in mart views using dim_scoring_format.
-- Source: raw.player_stats joined to dimensions.
-- ============================================

IF OBJECT_ID('warehouse.fact_player_week', 'U') IS NULL
CREATE TABLE warehouse.fact_player_week (
    fact_player_week_key    BIGINT IDENTITY(1,1) PRIMARY KEY,

    -- Dimension keys
    player_key              INT         NOT NULL,
    week_key                INT         NOT NULL,
    game_key                INT         NULL,

    -- Degenerate dimensions (carried for convenience)
    gsis_id                 VARCHAR(50) NOT NULL,
    season                  INT         NOT NULL,
    week                    INT         NOT NULL,
    recent_team             VARCHAR(5)  NULL,
    opponent_team           VARCHAR(5)  NULL,
    position                VARCHAR(10) NULL,

    -- Passing
    completions             INT         NULL DEFAULT 0,
    attempts                INT         NULL DEFAULT 0,
    passing_yards           DECIMAL(8,1) NULL DEFAULT 0,
    passing_tds             INT         NULL DEFAULT 0,
    interceptions           INT         NULL DEFAULT 0,
    sacks                   INT         NULL DEFAULT 0,
    sack_yards              DECIMAL(8,1) NULL DEFAULT 0,
    sack_fumbles_lost       INT         NULL DEFAULT 0,
    passing_air_yards       DECIMAL(8,1) NULL,
    passing_yac             DECIMAL(8,1) NULL,
    passing_first_downs     INT         NULL DEFAULT 0,
    passing_epa             DECIMAL(10,3) NULL,
    passing_2pt_conversions INT         NULL DEFAULT 0,

    -- Rushing
    carries                 INT         NULL DEFAULT 0,
    rushing_yards           DECIMAL(8,1) NULL DEFAULT 0,
    rushing_tds             INT         NULL DEFAULT 0,
    rushing_fumbles_lost    INT         NULL DEFAULT 0,
    rushing_first_downs     INT         NULL DEFAULT 0,
    rushing_epa             DECIMAL(10,3) NULL,
    rushing_2pt_conversions INT         NULL DEFAULT 0,

    -- Receiving
    receptions              INT         NULL DEFAULT 0,
    targets                 INT         NULL DEFAULT 0,
    receiving_yards         DECIMAL(8,1) NULL DEFAULT 0,
    receiving_tds           INT         NULL DEFAULT 0,
    receiving_fumbles_lost  INT         NULL DEFAULT 0,
    receiving_air_yards     DECIMAL(8,1) NULL,
    receiving_yac           DECIMAL(8,1) NULL,
    receiving_first_downs   INT         NULL DEFAULT 0,
    receiving_epa           DECIMAL(10,3) NULL,
    receiving_2pt_conversions INT       NULL DEFAULT 0,

    -- Usage / share
    target_share            DECIMAL(6,4) NULL,
    air_yards_share         DECIMAL(6,4) NULL,
    wopr                    DECIMAL(6,4) NULL,       -- Weighted Opportunity Rating

    -- Special teams
    special_teams_tds       INT         NULL DEFAULT 0,

    -- Source fantasy points (for validation, not primary use)
    source_fantasy_points       DECIMAL(8,2) NULL,
    source_fantasy_points_ppr   DECIMAL(8,2) NULL,

    -- Metadata
    loaded_at               DATETIME2   NOT NULL DEFAULT SYSUTCDATETIME(),

    -- Constraints
    CONSTRAINT fk_fpw_player FOREIGN KEY (player_key) REFERENCES warehouse.dim_player(player_key),
    CONSTRAINT fk_fpw_week   FOREIGN KEY (week_key)   REFERENCES warehouse.dim_week(week_key),
    CONSTRAINT fk_fpw_game   FOREIGN KEY (game_key)   REFERENCES warehouse.dim_game(game_key),
    CONSTRAINT uq_fpw_player_week UNIQUE (gsis_id, season, week)
);
GO

-- Index for common query patterns
CREATE NONCLUSTERED INDEX ix_fpw_season_week
    ON warehouse.fact_player_week (season, week)
    INCLUDE (player_key, recent_team, position);
GO

CREATE NONCLUSTERED INDEX ix_fpw_player
    ON warehouse.fact_player_week (player_key, season)
    INCLUDE (week, recent_team);
GO
