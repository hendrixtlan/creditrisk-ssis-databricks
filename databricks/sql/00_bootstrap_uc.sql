-- Prerequisites: UC-enabled workspace and admin grants.
-- FIRST register an Azure managed-identity storage credential and external location
-- covering abfss://landing@STORAGE_ACCOUNT.dfs.core.windows.net/ using UC admin UI.
-- Replace STORAGE_ACCOUNT below, and optionally creditrisk_dev.
CREATE CATALOG IF NOT EXISTS creditrisk_dev;
CREATE SCHEMA IF NOT EXISTS creditrisk_dev.ingest;
CREATE SCHEMA IF NOT EXISTS creditrisk_dev.bronze;
CREATE SCHEMA IF NOT EXISTS creditrisk_dev.silver;
CREATE SCHEMA IF NOT EXISTS creditrisk_dev.gold;
CREATE SCHEMA IF NOT EXISTS creditrisk_dev.ops;
CREATE EXTERNAL VOLUME IF NOT EXISTS creditrisk_dev.ingest.landing
  LOCATION 'abfss://landing@STORAGE_ACCOUNT.dfs.core.windows.net/';
CREATE VOLUME IF NOT EXISTS creditrisk_dev.ops.state;
-- Example (adjust principal names and privileges):
-- GRANT USE CATALOG ON CATALOG creditrisk_dev TO `creditrisk_engineers`;
-- GRANT USE SCHEMA, SELECT ON SCHEMA creditrisk_dev.gold TO `creditrisk_analysts`;
-- GRANT READ VOLUME ON VOLUME creditrisk_dev.ingest.landing TO `creditrisk_pipeline_sp`;
-- GRANT READ VOLUME, WRITE VOLUME ON VOLUME creditrisk_dev.ops.state TO `creditrisk_pipeline_sp`;
-- Grant write table permissions to service principal on bronze/silver/gold schemas.
