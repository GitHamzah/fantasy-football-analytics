-- ============================================
-- Seed dim_scoring_format with the three standard formats.
-- ============================================

IF NOT EXISTS (SELECT 1 FROM warehouse.dim_scoring_format WHERE format_name = 'Standard')
INSERT INTO warehouse.dim_scoring_format
    (format_name, pts_per_reception, pts_passing_yard, pts_passing_td, pts_interception,
     pts_rushing_yard, pts_rushing_td, pts_receiving_yard, pts_receiving_td,
     pts_fumble_lost, pts_2pt_conversion)
VALUES
    ('Standard',  0.0,  0.04, 4.0, -2.0, 0.1, 6.0, 0.1, 6.0, -2.0, 2.0),
    ('Half-PPR',  0.5,  0.04, 4.0, -2.0, 0.1, 6.0, 0.1, 6.0, -2.0, 2.0),
    ('PPR',       1.0,  0.04, 4.0, -2.0, 0.1, 6.0, 0.1, 6.0, -2.0, 2.0);
GO

-- ============================================
-- Seed dim_position with fantasy-relevant positions.
-- ============================================

IF NOT EXISTS (SELECT 1 FROM warehouse.dim_position WHERE position_abbr = 'QB')
INSERT INTO warehouse.dim_position
    (position_abbr, position_name, position_group, is_fantasy_relevant)
VALUES
    ('QB',  'Quarterback',    'QB',  1),
    ('RB',  'Running Back',   'RB',  1),
    ('FB',  'Fullback',       'RB',  1),
    ('WR',  'Wide Receiver',  'WR',  1),
    ('TE',  'Tight End',      'TE',  1),
    ('K',   'Kicker',         'K',   1),
    ('DEF', 'Team Defense',   'DEF', 1),
    ('DL',  'Defensive Line', 'DL',  0),
    ('LB',  'Linebacker',     'LB',  0),
    ('DB',  'Defensive Back', 'DB',  0),
    ('OL',  'Offensive Line', 'OL',  0),
    ('LS',  'Long Snapper',   'OL',  0),
    ('P',   'Punter',         'K',   0);
GO

PRINT 'Reference data seeded successfully.';
GO
