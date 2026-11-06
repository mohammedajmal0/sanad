-- One-time setup of Sanad's Unity Catalog objects. Run it in the SQL editor.
-- Safe to re-run: every statement uses IF NOT EXISTS.
-- Kept outside pipelines/transformations/ so the pipeline doesn't pick it up as code.

CREATE CATALOG IF NOT EXISTS sanad;

CREATE SCHEMA IF NOT EXISTS sanad.bronze;  -- raw data, exactly as received
CREATE SCHEMA IF NOT EXISTS sanad.silver;  -- cleaned and typed
CREATE SCHEMA IF NOT EXISTS sanad.gold;    -- business-ready answer tables
CREATE SCHEMA IF NOT EXISTS sanad.ai;      -- document chunks, tools (Phases 3 and 4)
CREATE SCHEMA IF NOT EXISTS sanad.ops;     -- audit, eval and monitoring tables

-- Landing zone: data_gen/ files are uploaded here, and Auto Loader reads from here.
CREATE VOLUME IF NOT EXISTS sanad.bronze.landing;
