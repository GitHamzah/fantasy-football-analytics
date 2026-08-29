{{ config(alias='formation') }}

-- Formation and personnel tendencies for the API/frontend layer.
-- One row per team-season-formation-personnel grouping.
--
-- Formation vocabulary is era-dependent (7 values through 2022, 3 from 2023),
-- so cross-era formation comparisons compare labels, not football.

SELECT * FROM {{ ref('fact_formation') }}
