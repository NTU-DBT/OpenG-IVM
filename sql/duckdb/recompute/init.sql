-- SOURCE_FILE: normal_test.sql
-- METHOD: recompute
-- TRANSFORMATIONS: no persistent objects needed for recompute
-- The recompute method creates session-local temporary objects in each query file.
SELECT 1 AS recompute_init_ok;
