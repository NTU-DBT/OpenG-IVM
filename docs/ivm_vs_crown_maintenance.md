# IVM vs CROWN maintenance — view-to-view and query-to-query

This document compares how the two incremental methods in this benchmark
maintain the Job 5 workload and answer its queries. Both maintain the **same
nine logical views** and produce **identical query results** at every step
(verified: 0 mismatches on DuckDB and openGauss). They differ in *what they
store* and *what they compute per step*.

- **IVM** (`maintain/ivm_maintain.py`) materializes all nine views as physical
  tables (`*_mv`). Each step, per view: find the affected keys, `DELETE` those
  rows, **re-join** the deltas against the base tables / other matviews, and
  `INSERT` the result. The join views actually store joined rows.
- **CROWN** (`maintain/crown_maintain.py`) materializes only selections,
  aggregates, and **projection views with derivation counts / semi-join
  flags**. Each step it updates counters and flags; **no join is computed
  during maintenance**. The joined rows are assembled at query time (and only
  when a query must emit full rows).

---

## 1. State each method maintains

| Logical view | IVM object (maintenance) | CROWN object (maintenance) | Same / different |
|---|---|---|---|
| `tmp_zx_send_countersign_t` (σ union) | `tmp_zx_send_countersign_t_mv` — one tagged table with `src_pk`; delete deleted src-pks, insert filtered new rows | `crown_src_ccci` + `crown_src_cici` — two per-branch σ-pushdown tables; delete + insert filtered rows | **Same idea** (selection pushdown) |
| `apt_mv` (γ MAX tax_invoice_date) | `apt_mv` — MERGE MAX + `_ivm_count`; group-local recalc on delete | `crown_agg_apt` — MAX fold + `cnt`/`cnt_nonnull`; group-local recalc on delete | **Essentially identical** |
| `temp_mv` (γ MAX approve_date) | `temp_mv` — same machinery as apt | `crown_agg_temp` — same machinery as apt | **Essentially identical** |
| `tic_mv` (SELECT DISTINCT) | `tic_mv` — `_ivm_count` reference counts | `crown_vp_tic` — derivation (reference) counts | **Essentially identical** |
| `tmp_cfs_opt…` (`oa ⋈ opii ⟕ pu ⟕ apt`) | `tmp_cfs_opt_application_inst_t_mv` — **materialized joined rows**; delete affected inst-ids, re-join `Δopii ⋈ oa` and `Δoa ⋈ opii` (+ pu, apt), insert; Δpu/Δapt pushed as UPDATEs | `crown_vs_oa` (σ-filtered `oa` + semi-join flags `flag_opii/flag_temp/flag_tic`) **plus** `crown_vp_opii` (π `operator_application_id` + count); `opii`/`pu` stay virtual | **Different** — join stored vs semi-join view + projection count |
| `approval_temp_mv` (`opt ⟕ task ⟕ route ⟕ node`) | `approval_temp_mv` — **materialized joined rows** (fan-out by task); delete + re-derive affected | *(not materialized)* — `approval_temp_cw` view assembled at query time | **Different** |
| `send_temp_mv` (`opt ⋈ temp ⟕ mes`) | `send_temp_mv` — **materialized joined rows**; delete + re-derive affected | *(not materialized)* — `send_temp_cw` view; `crown_mes` singleton kept separately | **Different** |
| `countersign_temp_mv` (`opt ⋈ tic`, **n:m** on application_code) | `countersign_temp_mv` — **materialized n:m join** (~367K rows at scale 0.1 for ~28K distinct ids); delete affected, re-join `opt ⋈ tic`, insert | *(not materialized)* — `countersign_temp_cw` view | **Different — the biggest gap** |
| `fact_t_mv` (UNION ALL of the three branches) | `fact_t_mv` — **materialized 35-column union** of all branch rows; delete affected ids, re-insert from the three branch matviews | `crown_fact_ids(id, cdc_last_update_date, cnt)` — only the id projection with a **fan-out count** (derivation counting); delete affected ids, re-derive per branch as a count lookup | **Different** — full joined rows vs distinct ids + count |

**Grouping the mechanism:**

- *Sources / aggregates / DISTINCT* (`tmp_zx`, `apt`, `temp`, `tic`): the two
  plans are the **same** — filtered insert/delete, MAX with a non-null counter
  and group-local recalc, and reference counting. CROWN's `crown_vp_tic` and
  IVM's `tic_mv._ivm_count` are literally the same counting.
- *The inst-core join* (`tmp_cfs_opt`): IVM keeps the joined rows current by
  re-joining deltas from both sides plus LEFT lookups, and pushes Δpu/Δapt as
  UPDATEs. CROWN instead maintains `crown_vp_opii` (a count per
  `operator_application_id`) and, via **S-Update**, flips the semi-join flags on
  `crown_vs_oa` when a child projection's liveness changes — no join.
- *The three branch joins + fact union* (`approval`, `send`, `countersign`,
  `fact`): IVM materializes and re-derives all of them (the bulk of its
  per-step cost — especially the n:m `countersign`). CROWN maintains **none** of
  the joined rows; it only maintains `crown_fact_ids`, the distinct fact ids
  annotated with their branch fan-out count (task-count / mes-count /
  DISTINCT-tic-count) — a per-key count lookup, no fan-out.

`fact_t_cw` (CROWN's fact view) is never materialized; it is a view assembled
on demand for q1 only.

---

## 2. Views used by the row-producing queries (q1–q4)

| Query | IVM reads | CROWN reads |
|---|---|---|
| **q1** detail-live | `fact_t_mv` (table scan) ⋈ dimension tables | `fact_t_cw` (view assembled from `crown_vs_oa`+flags, base `opii`/`pu`, `crown_agg_apt`, and per branch `task/route/node`, `crown_agg_temp`, `crown_vp_tic`) ⋈ dimension tables |
| **q2** detail-tombstone | `dtl` output + `NOT EXISTS` over the branch `*_mv` tables | `dtl` output + `NOT EXISTS` over the branch `*_cw` views |
| **q3** summary-live | group `dtl`, scope = `SELECT id FROM fact_t_mv WHERE cdc ≥ wm` | group `dtl`, scope = `SELECT id FROM fact_t_cw WHERE cdc ≥ wm` (assembled) |
| **q4** summary-tombstone | `sum` + `dtl` aggregate (output tables only) | identical — output tables only |

The one place IVM is cheaper is q1/q2: it scans a materialized fact/branch
table, whereas CROWN assembles the fact view to emit the full 35-column detail
rows. (Any method that materializes those rows pays this.)

---

## 3. Views used by the COUNT queries

The count queries return only `COUNT(*)` of each result, so CROWN never
assembles the join — it combines the maintained partial counts (annotations)
along the join tree. IVM still scans its materialized tables.

| Count query | IVM reads | CROWN reads (no join materialized) |
|---|---|---|
| **q1 count** (detail-live count) | `COUNT(*)` over `fact_t_mv ⋈ dims` | `crown_vs_oa` (+flags), base `opii` (inst-core), and **per-key count views**: `crown_vp_tic` (DISTINCT-tic-count per application_code), base `cfs_proc_task_t` (task-count per work_flow), `crown_mes` (mes-count); with the salesperson-region / non-OEM-contract / watermark filters. Count = Σ over the inst-core of `branch_multiplier × sprt_factor`. |
| **q2 count** (detail-tombstone count) | `COUNT(*)` over `dtl` with `NOT EXISTS` on branch `*_mv` | `dtl` output + `NOT EXISTS` over the **inst-core** (`crown_vs_oa ⋈ opii`, branch-flagged, not-deleted) — branch liveness of an id decided from `crown_vs_oa` flags, not a branch table |
| **q3 count** (summary group count) | `COUNT(*)` of groups over `dtl` scoped by `fact_t_mv` ids | `dtl` output + scope from `crown_fact_ids` (distinct ids); group set is multiplicity-invariant so the count needs no fan-out |
| **q4 count** (summary-tombstone count) | `COUNT(*)` over `sum` + `dtl` aggregate | identical — output tables only |

So the count queries exercise: `crown_vs_oa` (+ `flag_opii/flag_temp/flag_tic`),
`crown_vp_opii` (feeds `flag_opii`), `crown_vp_tic` (feeds `flag_tic` and the
per-code tic-count), `crown_agg_temp` (feeds `flag_temp`), `crown_mes` (mes
count), `crown_fact_ids` (q3 scope), and the retained `crown_src_ccci/cici`
that keep those aggregates/projections current — but **never** the assembled
fact or branch joins.

For the actual (row-producing) q3, CROWN also weights the summary `SUM`s by the
`cnt` column of `crown_fact_ids` (`SUM(x · cnt)`), which reproduces the
non-distinct scope's multiset SUMs exactly without expanding the fan-out
(`MAX` and DISTINCT-ordered `string_agg` are multiplicity-invariant).

---

## 4. Consequence

Same sources/aggregates/DISTINCT (identical maintenance); the plans diverge
entirely on the **join views**. IVM materializes and re-joins them (the inst
join, the three branch joins including the n:m `countersign`, and the fact
union); CROWN replaces those with a semi-join view + projection counts
(`crown_vs_oa` / `crown_vp_opii`) and a derivation-counted id view
(`crown_fact_ids`), assembling actual joined rows only when q1/q2 must emit the
full detail. This is why CROWN's per-step maintenance is markedly cheaper and
its count/aggregate queries never pay a join, at the cost of assembling the
fact view for the detail-emitting queries. See `results/` for the measured
numbers.
