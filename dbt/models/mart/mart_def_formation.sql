{{ config(alias='def_formation') }}

-- Defensive package and coverage-shell tendencies for the API layer.
-- One row per defensive team-season-package-shell.

SELECT * FROM {{ ref('fact_def_formation') }}
