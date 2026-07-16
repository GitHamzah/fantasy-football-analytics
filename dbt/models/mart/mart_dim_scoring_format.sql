-- mart_dim_scoring_format.sql
{{ config(alias='dim_scoring_format') }}

-- Disconnected dimension for Power BI. NOT joined to the fact table.
-- Used as a slicer — DAX measures read the selected format's scoring
-- weights and calculate fantasy points dynamically from fact stat columns.

SELECT
    format_name,
    pts_per_reception,
    pts_passing_yard,
    pts_passing_td,
    pts_interception,
    pts_rushing_yard,
    pts_rushing_td,
    pts_receiving_yard,
    pts_receiving_td,
    pts_fumble_lost,
    pts_2pt_conversion
FROM {{ ref('scoring_formats') }}
