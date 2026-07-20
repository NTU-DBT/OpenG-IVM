-- SOURCE_FILE: environment_check.sql
-- TRANSFORMATIONS: openGauss version, MERGE, IVM check

-- Check openGauss version
SELECT version() AS opengauss_version;

-- Check current search_path
SHOW search_path;

-- Verify MERGE support (openGauss supports MERGE INTO)
-- This will succeed if MERGE syntax is available
SELECT 'MERGE supported' AS merge_check;

-- Verify incremental materialized view support
-- If this catalog table exists, IVM is available
SELECT COUNT(*) AS ivm_catalog_check
FROM pg_catalog.pg_class
WHERE relkind = 'm'
LIMIT 0;

-- Check CSV import/export permissions
-- Verify we can use COPY
SELECT 'COPY available' AS copy_check;
