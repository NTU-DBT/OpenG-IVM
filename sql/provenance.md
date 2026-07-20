# SQL Provenance

Maps every generated SQL file to its source statements in the original benchmark files.

## DuckDB Init Files

| File | Source | Transformations |
|------|--------|----------------|
| `duckdb/init/00_create_schema_and_tables.sql` | `create_table_ddl.sql` | Schema prefix `IF NOT EXISTS`; DuckDB type mapping |
| `duckdb/init/01_create_primary_keys_and_indexes.sql` | `create_primary_key_ddl.sql` | Direct translation |
| `duckdb/init/02_load_static.sql` | Generated | `COPY FROM` for each static table CSV |
| `duckdb/init/03_load_base_100.sql` | Generated | `COPY FROM` for all 100 slices of each dynamic table |
| `duckdb/init/04_analyze.sql` | `analyze_normal.sql` | Single `ANALYZE;` for DuckDB |

## DuckDB Runtime Files

| File | Source | Transformations |
|------|--------|----------------|
| `duckdb/runtime/apply_insert.sql` | Generated | Fixed 5-slot COPY per dynamic table |
| `duckdb/runtime/load_delete_keys.sql` | Generated | CREATE TEMP TABLE + COPY for PK-only delete keys |
| `duckdb/runtime/apply_delete.sql` | Generated | DELETE USING temp key tables |
| `duckdb/runtime/count_base_rows.sql` | Generated | SELECT COUNT per dynamic table |

## DuckDB Recompute Queries

| File | Source Statement | Transformations |
|------|-----------------|----------------|
| `duckdb/recompute/q1_count.sql` | `normal_test.sql` 1st `INSERT...SELECT` | Removed INSERT; full CTE chain; `COUNT(*)` wrapper |
| `duckdb/recompute/q1_minmax.sql` | Same | MIN/MAX on id, application_code, submit_date, total_amount |
| `duckdb/recompute/q1_export.sql` | Same | `COPY TO` CSV |
| `duckdb/recompute/q2_*.sql` | `normal_test.sql` 2nd `INSERT...SELECT` | Tombstone detection via NOT EXISTS |
| `duckdb/recompute/q3_*.sql` | `normal_test.sql` 3rd `INSERT...SELECT` | Summary GROUP BY head_id |
| `duckdb/recompute/q4_*.sql` | `normal_test.sql` 4th `INSERT...SELECT` | Summary tombstone |

## DuckDB Logical Views

| File | Source Statement | Transformations |
|------|-----------------|----------------|
| `duckdb/logical_views/init.sql` | `create_matview.sql` all 9 views | `CREATE INCREMENTAL MATERIALIZED VIEW` -> `CREATE VIEW` |
| `duckdb/logical_views/q1-q4_*.sql` | Same as recompute | Uses named views instead of CTEs |

## DuckDB IVM

| File | Source Statement | Transformations |
|------|-----------------|----------------|
| `duckdb/ivm/init.sql` | `create_matview.sql` all 9 views | `CREATE TABLE AS SELECT` (physical tables) |
| `duckdb/ivm/maintain.sql` | `job5_ivm.sql` all MERGE statements | DROP+CTAS rebuild in dependency order; no persistent MLog |
| `duckdb/ivm/q1-q4_*.sql` | Same as logical_views | Reads physical tables |

## Dialect Adaptations

- `to_char(ts, 'yyyyMM')` -> `strftime(ts, '%Y%m')`
- `CAST(extract(epoch from current_timestamp) * 1000 AS VARCHAR)` -> `CAST(epoch_ms(CURRENT_TIMESTAMP) AS VARCHAR)`
- `STRING_AGG` preserved (DuckDB supports it)
- `group_concat(DISTINCT ... ORDER BY ... separator ',')` -> `string_agg(DISTINCT ..., ',' ORDER BY ...)`
- `GREATEST(bool, bool)` -> `GREATEST(CAST(bool AS INTEGER), CAST(bool AS INTEGER))::BOOLEAN`
- `NOW()` -> `CURRENT_TIMESTAMP`
- No join type, predicate, filter, grouping, UNION ALL, DISTINCT, or aggregate changes

## Index provenance (added 2026-07-19, openGauss runner)

**Target-table indexes** (all six per-method targets, identical across methods, spec §16):
`CREATE INDEX <dtl>_pk (id, logical_is_deleted)` / `CREATE INDEX <sum>_pk (head_id, logical_is_deleted)`.
Source: `create_primary_key_ddl.sql` declares `PRIMARY KEY (id)` on `dwd_billing_In_transit_dtl_t_05`
and `PRIMARY KEY (head_id)` on `dwd_billing_In_transit_t_05`. Our accumulate-only targets keep live and
tombstone rows for the same id, so the translated key is extended by `logical_is_deleted` — the same
identity used by the diff `NOT EXISTS`. Non-unique btree: identity is verified by cross-method result
comparison rather than a constraint.

**Matview indexes** (ivm method only; build time reported separately in the run log):
Source: `matview_info.out` shows every real openGauss matview carries a UNIQUE btree index —
`(ccci_ctid, cici_ctid)`, `(application_code)`, `(operator_application_id, application_inst_id,
pu_payment_unit_id, apt_ctid)`, `(oa_ctid, task_task_id, route_route_id, node_node_define_id)`,
`(application_code)`, `(oa_ctid, temp_ctid, mes_message_id)`, `(invoice_no, application_code, send_date)`,
`(oa_ctid, tic_ctid)`, `(approval_temp_mv_ctid, send_temp_mv_ctid, countersign_temp_mv_ctid)`.
Translation replaces physical ctid identity with the stable source keys probed by the translated
maintenance (`experiment_new/ivm_maintain.py`): see `MV_INDEX_DDL` in `opengauss_new/run.py`
(zx `(type, src_pk)` + `(application_code)`; apt `(application_code)`; opt `(application_inst_id)`,
`(operator_application_id)`, `(payment_unit_id)`, `(application_code)`; approval/send/countersign/fact
`(id)`; temp `(application_code)`; tic `(application_code)`).
DuckDB intentionally has no such indexes: its vectorized hash joins do not need them and ART index
maintenance would slow bulk DML; within-engine fairness is preserved (indexes identical across the
three methods where shared), cross-engine physical design is engine-appropriate and documented here.

**ANALYZE placement** (user directive 2026-07-18/19): static tables at init; dynamic tables at init only
for `preloaded_replacement_sliding` (after the 100% base load), otherwise after the first batch;
`mlog_ins_*` after the first batch, `mlog_del_*` at the first deleting step; matview tables at init for
preloaded (after CTAS + index build), otherwise after the first maintenance; the six target tables at
the end of step 1 (they only receive rows while step 1's queries run). All ANALYZE statements are
per-table and schema-scoped (a bare `ANALYZE` is database-wide and caused cross-scenario interference
in parallel runs). Durations are logged and excluded from every metric.

## v3 maintenance and planner adjustments (2026-07-19)

- `ivm_maintain.py` tic_mv matching: `application_code` now leads as a plain equality, with
  `invoice_no` / `send_date` keeping `IS NOT DISTINCT FROM`. Logically identical (application_code is
  never NULL: generator guarantee, verified 0 NULLs in zx/tic/apt/temp at full 0.1 scale) but hashable —
  openGauss cannot hash `IS NOT DISTINCT FROM` and executed a nested loop costing 183 s of the 220 s
  maintenance step. Same total semantics on DuckDB.
- `ivm_maintain.py` apt_mv/temp_mv insert guards: `c NOT IN (SELECT application_code FROM mv)` rewritten
  to `NOT EXISTS (SELECT 1 FROM mv t WHERE t.application_code = d.c)` — equivalent under the verified
  no-NULL guarantee, anti-hash-joinable (was ~9 s each per step).
- openGauss measured queries (all three methods, identically): session `SET enable_nestloop = off`.
  The estimator returns rows=1 after the tombstone self-anti-join and flipped q2 into nested-loop
  join-filter chains (observed 25 min and 56 min single-query stalls at preloaded steps 55/70);
  hash-join plans are stable. Soft switch; maintenance and DML sessions keep default settings
  (profiled: query_dop=1 doubles maintenance time; enable_nestloop=off is neutral there).
- Effect measured on the frozen preloaded step-55 state: maintenance 220.3 s -> 7.1 s per step.
