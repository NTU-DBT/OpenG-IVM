# CROWN Maintenance Plan for the Job 5 Streaming Query Workload

This document designs an incremental maintenance plan for the Job 5 workload
(`create_matview.sql`, `normal_test.sql`, `matview_test.sql`, `job5_ivm.sql`)
based on the change-propagation framework of:

> Qichen Wang, Xiao Hu, Binyang Dai, Ke Yi.
> **Change Propagation Without Joins.** PVLDB 16(5): 1046–1058, 2023.
> Full version: arXiv:2301.04003. System: CROWN (https://github.com/hkustDB/CROWN).

Section numbers refer to the PVLDB version unless marked *(full §…)* for the
arXiv full version.

The plan adopts the paper's framework with three deliberate adjustments:

1. **Propagating maintenance, SQL-join assembly, no enumeration.**
   Maintenance keeps the paper's change propagation: updates are propagated
   through **semi-join views and projection views** with derivation counting
   (the S-/P-/R-Update mechanics of §4, simulated with plain SQL). What is
   dropped is only the *enumeration procedure* (Algorithms 5–6, live views,
   delay guarantees): the final result of each query is assembled by
   **joining the maintained partial results in one SQL query**, leaving join
   order entirely to the engine's optimizer.
2. **No update-sequence analysis.** FIFO / insertion-only / enclosureness
   (§6) characterize theoretical update-cost upper bounds; they play no role
   in the algorithm itself and are not considered here.
3. **In-framework extensions for outer joins and MIN/MAX.** Both are
   maintained with the same state and update mechanics as the paper — they
   merely lose the theoretical per-update guarantee, which is not needed for
   this task. Their bookkeeping coincides with the "standard way" already
   captured in `job5_ivm.sql` (derivation counts `_ivm_count`, non-null
   aggregate counts `_ivm_count_<col>`, group-local `MAX` recalculation,
   DISTINCT reference counts), so line references `job5_ivm.sql L<n>` are
   given as provenance throughout.

The resulting method: **maintenance never materializes a join result — it
propagates deltas through semi-joins and projections; queries assemble the
final result by one join over the reduced state.**

The plan has been **verified executably**: `tools/crown_verify.py` implements
the maintenance algorithm below in DuckDB and checks it against ground-truth
recomputation after every update step — see §9.

---

## 1. Scope and sources

Maintenance targets are the nine incremental materialized views of
`create_matview.sql` and the query surface used by the four benchmark queries
(q1–q4 of `matview_test.sql` / `experiment_new/sql/*/query/`):

| Source object | Lines in `create_matview.sql` |
|---|---|
| `tmp_zx_send_countersign_t_mv` | 4–31 |
| `apt_mv` | 34–38 |
| `tmp_cfs_opt_application_inst_t_mv` | 40–70 |
| `approval_temp_mv` | 73–119 |
| `temp_mv` | 121–130 |
| `send_temp_mv` | 132–179 |
| `tic_mv` | 181–193 |
| `countersign_temp_mv` | 195–239 |
| `fact_t_mv` | 241–246 |

Base-table classification (from `experiment_new/data/manifests/tables.csv`):

* **Dynamic (streamed)**: `cfs_cinv_customer_invoice_t` (ccci),
  `cfs_inv_invoice_info_t` (cici), `cfs_opt_application_t` (oa),
  `cfs_opt_application_inst_t` (opii), `cfs_con_payment_unit_t` (pu),
  `cfs_proc_task_t` (task), `cfs_proc_route_t` (route), `tpl_fd_message_t`
  (mes), `cfs_cfg_company_t`, `cfs_comm_contract_t`, `tpl_user_t`.
* **Static**: `cfs_proc_node_define_t` (node), `cfs_comm_currencies_t`,
  `cfs_comm_customer_t`, `cfs_comm_invtype_t`, `cfs_salesperson_region_t`,
  `dwd_job_status_t_05`.

`cfs_cfg_company_t`, `cfs_comm_contract_t`, and `tpl_user_t` are dynamic but
appear **only in the top-level queries** (query-time dimension joins in all
methods); they are outside the maintenance plan.

---

## 2. The framework, as used here

For a query decomposed over a join tree, CROWN maintains per node `e` a
**semi-join view** `V_s(R_e) = R_e ⋉ V_p(child_1) ⋉ … ⋉ V_p(child_k)` and a
**projection view** `V_p(R_e) = π_key(e) V_s(R_e)` with **derivation
counting** (§4, Eqs. 2–4): each `V_p` tuple carries the number of supporting
`V_s` tuples, and each `V_s` tuple tracks which child `V_p`s it currently
matches. An update to a relation triggers an R-Update on its own node, and
the resulting `V_p` changes propagate upward as S-/P-Updates — counter
adjustments simulated by semi-joins and projections, **never by a join**.
Every maintained view is linear in the input (Lemma 4.1).

Selections local to one relation are applied once at update time, so filtered
tuples never enter the state *(full §7.2)*. Unions whose branches are made
disjoint by constant tags are maintained per branch *(full §7.2)*.
Aggregations ride along as annotations on the same counters *(full §7.3,
Eqs. 10–13)*: `COUNT`/`SUM` form a commutative ring and absorb arbitrary
updates in place.

**Result assembly (adjustment 1).** The paper enumerates results from the
reduced views with constant delay; here, each result view of the workload is
instead declared as an **ordinary SQL view joining the maintained partial
results in one query**. Join order is left to the engine — the concern the
enumeration procedure addresses does not apply. Because the propagation has
already semi-join-reduced the state, the assembly join starts from exactly
the participating tuples.

**Extensions (adjustment 3).**

* **Outer joins**: an outer-joined child is a *non-reducing edge* — its state
  is maintained exactly like any other (with counters/aggregates if it has a
  selection, DISTINCT, or GROUP BY), but it contributes no semi-join factor
  to its parent's `V_s` and no liveness requirement. The padding semantics
  (`NULL` extension when no partner exists) are realized by the `LEFT JOIN`
  operator in the assembly query. Same state, same update rules, no
  theoretical guarantee needed.
* **MIN/MAX**: maintained as an aggregate annotation with the same group
  counters. `(dom, max)` is a semiring without additive inverses *(full §7.3
  footnote 6)*, so insertions fold in place (`max := greatest(max, v)`) while
  a deletion that may remove the current extremum triggers a **group-local
  recalculation** from the retained source-side partial result — which the
  framework keeps anyway. No per-update guarantee; identical bookkeeping to
  `job5_ivm.sql`'s `_ivm_count_<col>` mechanics.

---

## 3. Operation inventory and supportability matrix

### 3.1 Generic operations

| Operation in the workload | Status | Treatment |
|---|---|---|
| Single-relation selection (`status` codes, `application_type = 1`, `creation_date > '2022-01-01'`, `IS NULL` tests, mes constants) | ✔ *(full §7.2)* | applied at update time; rejected tuples never enter state |
| Projection / `SELECT DISTINCT` (`tic_mv`) | ✔ core | `V_p` with derivation counting; row live iff count > 0 |
| `UNION ALL` with disjoint constant tags | ✔ *(full §7.2)* | per-branch maintenance; disjoint tags ⇒ per-branch deltas |
| Inner equi-join (`oa ⋈ opii`, `⋈ temp`, `⋈ tic`) | ✔ core | **never materialized**: maintained as semi-join reductions (`V_s` flags fed by child `V_p` liveness); the join itself runs in the assembly SQL |
| `COUNT`, `SUM` | ✔ ring *(full §7.3)* | in-place annotation updates under insert and delete |
| `MAX` (`apt_mv`, `temp_mv`) | ✔ **extension** | fold on insert; group-local recalc when the extremum may be deleted (§6.1); no theoretical guarantee |
| `LEFT JOIN` (pu, apt, task→route→node, mes) | ✔ **extension** | non-reducing edges; `LEFT JOIN` in the assembly SQL (§6.2); no theoretical guarantee |
| Per-tuple scalars (`to_char`, `CAST`, constants, `CASE`) | ✔ trivial | evaluated in the assembly views |
| Multi-relation scalars/predicates (`greatest`, `COALESCE(sprt1…, sprt2…)`, q1 watermark) | ✔ trivial here | evaluated in the assembly / query SQL (all inputs present at query time) |
| Volatile expressions (`NOW()`, `current_timestamp`, `_hoodie_event_time`) | query-time | evaluated when the view is queried (same semantics as the `logical_views` method); normalized in comparisons per the experiment rules |
| Order-sensitive aggregates (`STRING_AGG`, `group_concat DISTINCT` in q3/q4) | query-time | remain inside the fixed q3/q4 files, as in every method |

### 3.2 Per-view classification

| # | View | Structure | Decision |
|---|---|---|---|
| 1 | `tmp_zx_send_countersign_t_mv` | `σ(status≥3) ccci` (tag '1') `UNION ALL` `σ(status∈{30,40}) cici` (tag '2') | **two maintained filtered sources** (`crown_src_ccci`, `crown_src_cici`); the union itself is never materialized — consumers read the branch that concerns them |
| 2 | `apt_mv` | `γ_application_code MAX(tax_invoice_date)` over tag-'1' rows | **maintained aggregate state** with MAX extension (§6.1); non-reducing (LEFT-joined) |
| 3 | `tmp_cfs_opt_application_inst_t_mv` | `oa ⋈ opii` `⟕ pu` `⟕ apt`, selections on `oa`, `greatest()` scalars | **not materialized**: `V_s(oa)` with semi-join flag fed by `V_p(opii)`; the joins run in the assembly views |
| 4 | `approval_temp_mv` | `σ(status=30)` core `⟕ task ⟕ route ⟕ node`, `NOW()` columns | **assembly view** over the reduced core + virtual relations |
| 5 | `temp_mv` | `γ_application_code MAX(approve_date)` over `σ(status=30)` of both tags | **maintained aggregate state** with MAX extension (§6.1); reducing — its group liveness gates the send branch (§4) |
| 6 | `send_temp_mv` | `σ(status=40)` core `⋈ temp` on group key `⟕ mes` | **assembly view**; `temp` read from aggregate state; `mes` from a maintained filtered singleton |
| 7 | `tic_mv` | `SELECT DISTINCT π(invoice_no, application_code, send_date)` over `σ(status≥40 ∧ (office_receive_date IS NULL ∨ customer_receive_date IS NULL))` of both tags | **maintained `V_p`** with derivation counting — the "DISTINCT reference count" of `job5_ivm.sql` L81 *is* this counter; reducing — its per-code liveness gates the countersign branch |
| 8 | `countersign_temp_mv` | `σ(status=50)` core `⋈ tic` on `application_code` (non-key, n:m) | **assembly view** — the n:m join that standard IVM materializes is deferred to query time over the reduced core |
| 9 | `fact_t_mv` | `UNION ALL` of views 4/6/8, disjoint by `node_type` | **assembly view** = `UNION ALL` of the three branch views; keeps its name so the fixed q1–q4 files run unchanged |

The workload's generator guarantees duplicate `application_code`s and multiple
invoice rows per code, so the joins through `application_code` (views 6, 8)
are genuinely n:m. The standard framework materializes their results
(`send_temp_mv`, `countersign_temp_mv`, and their `MERGE` maintenance in
`job5_ivm.sql` L74–L86); this plan never stores a joined row.

---

## 4. Join trees and maintained state

### 4.1 Per-branch join trees

All three branches share the core key join `oa ⋈ opii` on
`operator_application_id`; selections on `oa` are applied at update time, and
`status ∈ {30,40,50}` partitions the core into the three branches. Solid
edges are reducing (semi-join factors); dashed edges are non-reducing outer
extensions (§6.2):

```
     approval (status=30)         send (status=40)           countersign (status=50)
        oa ──── opii                 oa ──── opii                oa ──── opii
        ┆                            │                           │
        ┆ task ─ route ─ node        │ temp [application_code]   │ tic [application_code]
        ┆ (⟕ chain)                  │ (MAX state, reducing)     │ (DISTINCT V_p, reducing)
        ┆                            ┆ mes (⟕ singleton)         │
        ┆ pu, apt (⟕ lookups)        ┆ pu, apt (⟕ lookups)       ┆ pu, apt (⟕ lookups)
```

`V_s(oa)` therefore keeps one semi-join match flag per reducing child:
`flag_opii` (fed by `V_p(opii)`), `flag_temp` (fed by `temp` group liveness,
status-40 rows), `flag_tic` (fed by live-`tic`-code liveness, status-50
rows). A core row participates in its branch iff its σ predicates hold and
its branch-relevant flags are true — the paper's
"`count[t] = |C_e|`" membership condition (Algorithm 4), stored as explicit
flags for clarity.

### 4.2 State schema

Physical tables (both engines; prefix `crown_`). "cnt" columns are CROWN
derivation counters. All state is linear in the live base data (Lemma 4.1).

| State table | Role | Key | Extra columns | Secondary indexes |
|---|---|---|---|---|
| `crown_src_ccci` | `V_s` of `σ(status ≥ 3)` ccci, tag '1' | `customer_invoice_id` | application_code, approve_date, status, invoice_no, send_date, office_receive_date, customer_receive_date, tax_invoice_date | (application_code) |
| `crown_src_cici` | `V_s` of `σ(status ∈ {30,40})` cici, tag '2' (receive dates ≡ NULL, tax_invoice_date ≡ NULL) | `invoice_id` | application_code, approve_date, status, invoice_no (= tax_invoice_no), send_date | (application_code) |
| `crown_agg_apt` | apt groups over tag-'1' rows | `application_code` | `max_tax_invoice_date`, `cnt` (= `_ivm_count`), `cnt_nonnull` (= `_ivm_count_tax_invoice_date`) | — |
| `crown_agg_temp` | temp groups over `σ(status=30)` of both tags | `application_code` | `max_approve_date`, `cnt`, `cnt_nonnull` | — |
| `crown_vp_tic` | live DISTINCT triples of `tic_mv` with reference counts | (`invoice_no`, `application_code`, `send_date`) | `cnt` | (application_code) |
| `crown_vp_opii` | `V_p(opii)` = π_operator_application_id with counts | `operator_application_id` | `cnt` | — |
| `crown_vs_oa` | `V_s(oa)` = σ-filtered oa **+ semi-join flags** | `operator_application_id` | all `oa` columns used downstream + `flag_opii`, `flag_temp`, `flag_tic` | (application_code), (work_flow_id) |
| `crown_mes` | `σ(app_name='cfs' ∧ language='zh_CN' ∧ message_key='cfs.html.label.role.operatorInvoiceSender')` tpl_fd_message_t (expected singleton) | `message_id` | message | — |

Virtual relations (no maintained state; the assembly views read the base
tables through their indexes): `opii` (PK + (operator_application_id),
(payment_unit_id)), `pu` (PK), `task` (PK + (proc_inst_id), (route_id)),
`route` (PK), `node` (PK, static), and all query-time dimension tables.

Notes.

* `crown_src_ccci` / `crown_src_cici` serve double duty: they are the
  selection-pushdown partial results of view 1 *and* the retained source
  states from which the MAX recalculation of §6.1 reads.
* `opii` is a leaf without a filter, so its `V_s` equals the base table and
  stays virtual; only its projection `crown_vp_opii` is maintained. Because
  the state does not retain `opii` rows, the delta staging must capture the
  old rows of deleted `opii` keys **before** the base delete (same
  transaction) — the verification harness demonstrates this (§9).
* No MLogs, no CSNs, no `ctid` identity, no persistent staging. Deltas are
  read from the experiment's fixed CSV slots; old attribute values of deleted
  rows are recovered from the `crown_*` state by primary key (or, for virtual
  leaves, from the base table before deletion).

---

## 5. Result assembly views

Declared once at method initialization as **ordinary (non-materialized)
views**, preserving the expressions, join types, filters, and output columns
of `create_matview.sql`. The FROM sources are the maintained partial results;
the core is gated by the semi-join flags. Final results are produced by
*joining the partial results in one SQL query* — join order is the engine's
business.

```sql
-- inst core (view 3, never materialized):
--   (SELECT * FROM crown_vs_oa
--     WHERE flag_opii AND (status = 30 OR (status = 40 AND flag_temp)
--                                     OR (status = 50 AND flag_tic))) oa
--   JOIN opii            ON oa.operator_application_id = opii.operator_application_id
--   LEFT JOIN pu         ON opii.payment_unit_id = pu.payment_unit_id
--   LEFT JOIN crown_agg_apt apt ON oa.application_code = apt.application_code
--   (greatest()/scalar expressions verbatim)

CREATE VIEW approval_temp_mv AS      -- view 4
  SELECT … FROM inst-core WHERE status = 30
  LEFT JOIN task  ON oa.work_flow_id = task.proc_inst_id
  LEFT JOIN route ON task.route_id = route.route_id
  LEFT JOIN node  ON route.node_define_id = node.node_define_id;

CREATE VIEW send_temp_mv AS          -- view 6
  SELECT … FROM inst-core WHERE status = 40
  JOIN crown_agg_temp temp ON temp.application_code = oa.application_code
  LEFT JOIN crown_mes mes ON (true);

CREATE VIEW countersign_temp_mv AS   -- view 8
  SELECT … FROM inst-core WHERE status = 50
  JOIN crown_vp_tic tic ON tic.application_code = oa.application_code;

CREATE VIEW fact_t_mv AS             -- view 9
  SELECT <35 columns> FROM approval_temp_mv
  UNION ALL SELECT … FROM send_temp_mv
  UNION ALL SELECT … FROM countersign_temp_mv;
```

Semantics notes (checked against `create_matview.sql`):

* `crown_agg_apt` participates via LEFT JOIN keyed by the group key: a live
  group contributes its `max_tax_invoice_date` (NULL when `cnt_nonnull = 0`),
  a dead/absent group pads with NULL — the original `apt_mv` semantics
  including the `_ivm_count`-style group liveness of `job5_ivm.sql` L50.
* `crown_agg_temp` participates via INNER JOIN and additionally gates the
  core through `flag_temp`: group death both flips the flag and (at query
  time) eliminates the send rows of that code.
* `crown_vp_tic` exposes only rows with `cnt > 0`; the n:m fan-out to
  countersign rows happens in the view execution.
* `mes` is formally 0..n (three constant predicates, no key); the generator
  guarantees exactly one matching row; the state keeps all matching rows so
  the view reproduces exact `LEFT JOIN` semantics regardless.
* Volatile columns (`NOW()`, `_hoodie_event_time`) are evaluated when a query
  executes the view — the same behavior as the `logical_views` method; they
  do not reach `fact_t_mv`'s column list and are normalized in comparisons
  per the experiment rules.
* Because q2/q4's `NOT EXISTS (… WHERE logical_is_deleted_del IS FALSE AND
  oa.id = …)` subqueries reference `approval_temp_mv` / `send_temp_mv` /
  `countersign_temp_mv` by name, declaring the assembly views under exactly
  these names lets **all twelve fixed query files run unchanged**.

---

## 6. Maintenance procedure (change propagation)

One fixed maintenance SQL file per engine, executed inside the same
transaction as the base-table updates. Propagation runs bottom-up through the
state, in this order:

```
(0) Stage step deltas from the fixed CSV slots: ins_<t> (full rows) and
    del_<t> (PK sets). Old attribute values of deleted rows are recovered
    from the crown_* state by PK; for the virtual leaf opii, the old rows of
    deleted keys are read from the base table before the delete applies.

(1) Sources (R-Update + σ at update time):
      upsert/delete crown_src_ccci, crown_src_cici.
(2) Aggregate projections (P-Update with annotations):
      fold source deltas into crown_agg_apt and crown_agg_temp by the MAX
      rules of §6.1; record temp-group births/deaths.
(3) DISTINCT projection (P-Update): adjust crown_vp_tic reference counts
      from σ(status≥40 ∧ recv-null) source deltas; insert at 0→1, delete at
      1→0; record per-application_code liveness births/deaths.
(4) V_p(opii) (R-Update + projection): fold Δopii into crown_vp_opii counts;
      record key births/deaths.
(5) S-Update — propagate child liveness transitions into V_s(oa) flags:
      flag_opii := true/false for oa rows whose operator_application_id was
      born/died in (4); flag_temp, flag_tic likewise from (2)/(3) by
      application_code (via the secondary indexes).
(6) R-Update on oa: delete crown_vs_oa rows for del_oa keys; insert
      σ-passing ins_oa rows with flags computed by direct lookups against
      the post-state of (2)–(4).
(7) mes singleton (R-Update + σ): upsert/delete crown_mes.
```

No step materializes a join: (1)–(4) and (6)–(7) touch one relation's state
each; (5) is a semi-join-shaped counter/flag update driven by key sets. Base
deltas of the purely virtual relations `pu`, `task`, `route` require no
propagation at all — they sit behind non-reducing edges, so their effects
surface through the assembly views at the next query.

### 6.1 MIN/MAX extension (`apt_mv`, `temp_mv`)

Provenance: `job5_ivm.sql` L50 (`_ivm_count`, `_ivm_count_tax_invoice_date`)
and L71 (`_ivm_count_approve_date`); *(full §7.3 fn. 6)* for why deletions
cannot fold in place.

Per group `g`, state = (`cnt`, `cnt_nonnull`, `max_…`):

* **insert** v: `cnt++`; if v non-null: `cnt_nonnull++`,
  `max := greatest(max, v)` — pure in-place fold;
* **delete** v: `cnt--`; if v non-null: `cnt_nonnull--`; then
  * `cnt = 0` → delete the group row (group death; propagated to `flag_temp`
    in step (5) for temp; apt is non-reducing, so the assembly LEFT JOIN
    simply pads NULL);
  * else `cnt_nonnull = 0` → `max := NULL`;
  * else if v may equal the current max (`v ≥` stored max after folding the
    step's inserts) → **group-local recalculation**: recompute `max_…` from
    the retained source state (`crown_src_ccci` for apt; `σ(status=30)` of
    `crown_src_ccci ∪ crown_src_cici` for temp) via the `(application_code)`
    index — never a full scan, never a base-table scan;
  * else no change.

Cost is bounded by the affected group's size, only when the extremum may have
left — the accepted price of losing the ring property; no theoretical
guarantee, per the task's framing.

### 6.2 Outer-join extension

The outer-joined relations are either virtual (`pu`, `task`, `route`, `node`)
or already-maintained partial results (`crown_agg_apt`, `crown_mes`); as
non-reducing edges they impose no flags on the preserved side, and the
padding semantics are produced by the `LEFT JOIN` operators inside the
assembly views (§5). (If one later wanted to semi-join-reduce an outer child
— e.g. keep only `pu` rows referenced by some `opii` — the same
derivation-counter machinery applies, without guarantees; it is unnecessary
at this workload's scale.)

---

## 7. Cost characteristics (qualitative)

No update-sequence analysis (FIFO, insertion-only, enclosureness) is used —
per-scenario behavior differs only in which deltas arrive, not in the
algorithm.

* **Maintenance**: no join is ever materialized. Per step: O(|Δ|) state
  upserts for ccci/cici/oa/opii/mes deltas; flag propagation proportional to
  the number of oa rows whose child liveness actually flipped (index-assisted
  semi-join updates); group-local MAX recalcs only when a deletion may remove
  a group's extremum (bounded by group size); nothing for pu/task/route
  deltas.
* **Space**: linear — filtered/aggregated/projected images of single
  relations, plus counters and flags. Contrast: the standard plan
  materializes all nine views including the n:m join views (`send_temp_mv`,
  `countersign_temp_mv`, `job5_ivm.sql` L74–L86) plus 27 MLogs (19
  base-table + 8 matview, L4–L33); the `logical_views` method stores nothing
  but re-derives every σ/DISTINCT/MAX from full base tables at each query.
* **Query time**: each benchmark query assembles the result with one join
  over partial results that are already filtered (`crown_vs_oa`,
  `crown_src_*`), semi-join-reduced (flags), de-duplicated (`crown_vp_tic`),
  or pre-aggregated (`crown_agg_*`) — dangling tuples never reach the
  assembly join, and the per-query work the `logical_views` method spends on
  selections, DISTINCT, and grouping is already paid incrementally.

---

## 8. Query-form integration

The four logical queries with their three fixed forms each (count / fixed
MIN-MAX / full CSV export, `experiment_new/sql/<engine>/query/
q{1..4}_{count,minmax,export}.sql`) run **unchanged**, because
`fact_t_mv`, `approval_temp_mv`, `send_temp_mv`, and `countersign_temp_mv`
exist under their original names as assembly views (§5):

* **q1 (detail live)**: `fact_t_mv` ⋈ dimension tables at query time,
  residual predicates (watermark, sprt IS NOT NULL, non-OEM) verbatim.
* **q2/q4 (tombstones)**: `NOT EXISTS` anti-joins run against the branch
  assembly views directly.
* **q3 (summary live)**: `STRING_AGG`/`group_concat` grouping stays inside
  the fixed query file.

Each form re-executes the view expansion independently, per the experiment's
repeated-execution rule (no cached-result reuse across the three forms).
Counts and MIN/MAX must agree with `recompute` / `logical_views` / `ivm` at
every step, and exports as multisets — the experiment's existing validation
applies verbatim as the acceptance test for this plan.

---

## 9. Verification (executed)

`experiment_new/tools/crown_verify.py` implements this plan end-to-end in
DuckDB on synthetic data and checks it after **every** update step:

* **Result equivalence**: multiset equality (`EXCEPT ALL` both directions) of
  the four result views — approval, send, countersign, fact — between the
  CROWN assembly (§5 over the propagated state) and ground truth (the
  workload's original view definitions recomputed over the base tables).
* **State invariants**: `crown_agg_apt` / `crown_agg_temp` (cnt, cnt_nonnull,
  max) equal a fresh recomputation; `crown_vp_tic` reference counts equal
  recomputation; `crown_vp_opii` counts equal recomputation; `crown_vs_oa`
  membership **and all three semi-join flags** equal recomputed semi-join
  membership; counters non-negative and `cnt_nonnull ≤ cnt`.

Scenario driven per seed: initialization from preloaded data, 4 insert-only
steps, 10–20 mixed insert+delete steps (~6% random deletions per table per
step), targeted probes, and 3 delete-heavy steps (~35% per step) that drain
the database. Probes cover exactly the extension edge cases: deleting the row
holding a group's current MAX; killing an entire temp group (send rows must
vanish via both flag and join) and an entire apt group (column must pad
NULL); outer-join padding toggles (first task for a workflow, then its
removal); deleting and re-inserting the matching mes singleton; deleting all
`opii` children of a live `oa` (flag must flip) and deleting an `oa` that
still has children.

Result: **all checks pass on every step** for seeds 42 (29 steps) and 7, 123,
2026 (39 steps each) — `ALL CHECKS PASSED: CROWN maintenance == ground-truth
recomputation on every step, and all state invariants hold.`

One implementation lesson the harness surfaced (now §4.2): for the virtual
leaf `opii`, the old rows of deleted keys must be captured **before** the
base delete applies — recovering them afterwards silently loses the `V_p`
decrements (the result views still matched for a while because counts only
drifted upward, but the state invariants caught it immediately; this is why
the harness checks state, not just results).

Run it: `python3 experiment_new/tools/crown_verify.py [--seed N]
[--steps-mixed N] [--verbose]`; exit code 0 iff everything passes.

**Benchmark comparison (executed).** `experiment_new/crown_compare/` runs
this plan as a third method beside `recompute` and `ivm` on the real
experiment data at scale 0.1, all three scenarios, 20 steps each, on **both
engines**: identical query results everywhere (all per-step count/min-max
checks and all 21 final multiset comparisons pass per engine, and counts
agree across engines). Median maintenance per step, crown vs ivm — DuckDB:
0.31 vs 2.06s (insertion), 0.48 vs 0.62s (sliding), 0.53 vs 3.42s
(preloaded); openGauss: 1.22 vs 6.11s, 1.86 vs 2.53s, 2.37 vs 10.79s.
Query costs are comparable on DuckDB; on openGauss ivm's materialized reads
are cheaper on q3 while crown stays well below recompute. Two engine-side
implementation idioms matter on openGauss (equality on the non-NULL group
key in the DISTINCT-view match; `NOT EXISTS`-materialized born/died sets) —
see `crown_compare/README.md` and `crown_compare/results/*/report.md`.

---

## 10. Implementation sketch (follow-up, not in this change)

* Add a **fourth runner method `crown`** with the same fixed-file contract as
  the others: `sql/<engine>/crown/init.sql` (create + initially populate the
  eight state tables from the loaded base data; declare the assembly views)
  and `sql/<engine>/crown/maintain.sql` (the fixed §6 procedure reading the
  current CSV slots); the `query/` files are shared and unchanged.
  `tools/crown_verify.py` already contains both scripts in engine-neutral
  form (its `CROWN_STATE_SQL`, `CROWN_ASSEMBLY_SQL`, `MAINTAIN_SQL`
  constants) and serves as the reference implementation.
  ⚠ The experiment specification currently mandates **exactly three
  methods**; adding `crown` needs an explicit spec amendment / user sign-off
  before implementation.
* Both engines use plain tables + `MERGE`/upsert; no engine-specific IVM
  internals are touched (no MLogs, CSNs, or `ctid`), so the same plan runs on
  DuckDB and any openGauss build, including openGauss-lite.
* For `preloaded_replacement_sliding`, the state tables are populated after
  the 100% preload by running their defining queries once (initialization
  cost, reported separately per the experiment's timing rules).

## Provenance summary

| This document's mechanism | Source |
|---|---|
| tagged per-branch source states (union) | `create_matview.sql` L4–31; `job5_ivm.sql` L45, L47 (two per-branch `MERGE`s) |
| derivation counts (`cnt`) and semi-join flags | `_ivm_count` columns throughout `job5_ivm.sql`; CROWN §4, Algorithms 2–4 |
| `cnt_nonnull` + group-local MAX recalc | `job5_ivm.sql` L50 (`_ivm_count_tax_invoice_date`), L71 (`_ivm_count_approve_date`); *(full §7.3 fn. 6)* |
| DISTINCT reference counting (`crown_vp_tic`) | `job5_ivm.sql` L81; CROWN `V_p` counting |
| joins assembled at query time (never materialized) | CROWN §1/§4 (join-free plans); replaces the per-source `MERGE` arms `job5_ivm.sql` L53–L94 |
| outer joins & MIN/MAX as in-framework extensions without guarantees | task instruction; *(full §7.2–7.3)* boundary discussion |
| executable verification | `experiment_new/tools/crown_verify.py` (§9) |
