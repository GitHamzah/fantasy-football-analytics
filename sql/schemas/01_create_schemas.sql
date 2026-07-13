-- ============================================
-- Create schemas for the FantasyFootball warehouse
-- Run this once against the FantasyFootball database.
-- ============================================

IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'raw')
    EXEC('CREATE SCHEMA raw');
GO

IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'staging')
    EXEC('CREATE SCHEMA staging');
GO

IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'warehouse')
    EXEC('CREATE SCHEMA warehouse');
GO

IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'mart')
    EXEC('CREATE SCHEMA mart');
GO

PRINT 'All schemas created successfully.';
GO
