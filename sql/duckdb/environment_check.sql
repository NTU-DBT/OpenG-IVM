-- SOURCE_FILE: environment_check.sql
-- TRANSFORMATIONS: DuckDB version check
SELECT version() AS duckdb_version;
SELECT current_schema() AS current_schema;
