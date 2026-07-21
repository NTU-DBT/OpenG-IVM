#!/usr/bin/env python3
"""CROWN-style incremental maintenance for the Job 5 workload.

Implements the plan in docs/crown_maintenance_plan.md: maintenance propagates
deltas through semi-join views (V_s) and projection views (V_p) with
derivation counting (S-/P-/R-Update simulated in SQL); it never materializes a
join. Final results are assembled at query time by ordinary SQL views (*_cw)
that join the maintained partial results. Outer joins and MIN/MAX are handled
as in-framework extensions (non-reducing edges; group counters with
group-local recalculation on extremum deletion).

Two dialects, mirroring maintain/ivm_maintain.py: DuckDB (MERGE, CREATE OR
REPLACE TEMP, SELECT * EXCLUDE) and openGauss (UPDATE..FROM + INSERT..NOT
EXISTS, DROP+CREATE TEMP, explicit column lists). The DuckDB path reads
deltas from temp tables `_ins_*` / `_del_*`; the openGauss path from the
persistent MLog-analog tables `mlog_ins_*` / `mlog_del_*`.

State tables (both engines): crown_src_ccci, crown_src_cici (selection
pushdown + retained source for MAX recalc), crown_agg_apt / crown_agg_temp
(MAX groups with cnt/cnt_nonnull), crown_vp_tic (DISTINCT reference counts),
crown_vp_opii (FK projection counts), crown_vs_oa (semi-join view with
flag_opii / flag_temp / flag_tic), crown_mes (constant-selected singleton).
"""

MSG_KEY = "cfs.html.label.role.operatorInvoiceSender"

MV_NAMES = ["tmp_zx_send_countersign_t_mv", "apt_mv",
            "tmp_cfs_opt_application_inst_t_mv", "approval_temp_mv",
            "temp_mv", "send_temp_mv", "tic_mv", "countersign_temp_mv",
            "fact_t_mv"]

CROWN_TABLES = ["crown_src_ccci", "crown_src_cici", "crown_agg_apt",
                "crown_agg_temp", "crown_vp_tic", "crown_vp_opii",
                "crown_vs_oa", "crown_mes", "crown_fact_ids"]

OA_COLS = ("operator_application_id, application_code, salesperson_id, company_id, "
           "customer_id, currency_id, total_amount, creation_date, applicant_time, "
           "logical_is_deleted, cdc_last_update_date, work_flow_id, application_type, status")
OA_FILTER = ("application_type = 1 AND status IN (30, 40, 50) "
             "AND creation_date > TIMESTAMP '2022-01-01 00:00:00'")
CCCI_COLS = ("customer_invoice_id, application_code, approve_date, status, invoice_no, "
             "send_date, office_receive_date, customer_receive_date, tax_invoice_date")

# columns excluded from cross-method output comparison: volatile NOW()-stamped
# columns, and (for the summary table) order-sensitive string_agg columns.
VOLATILE_COLS = {"rtd_last_update_date", "src_cdc_event_date",
                 "src_cdc_last_update_date", "_hoodie_event_time"}
UNORDERED_AGG_COLS = {"contract_number", "customer_pono",
                      "hw_contract_bussource_code", "project_number",
                      "project_name", "billing_status", "frame_contract_no"}


def _oa_cols(prefix="oa."):
    return ", ".join(prefix + c.strip() for c in OA_COLS.split(","))


# ==========================================================================
# crown_fact_ids: the id column of fact_t_cw, materialized and maintained
# ==========================================================================
#
# Q3's scope needs only fact_t.id (+ cdc for the watermark), but as a *bag*:
# fact_t is a UNION ALL of three branch views and its id fan-out (n:m tic in
# countersign, 1:n task in approval) is real: the non-distinct scope join
# multiplies the summary SUMs, and ivm/recompute reproduce that, so crown must
# too. Rather than store the exploded bag, we use derivation counting: keep the
# DISTINCT fact ids each annotated with their fan-out count, and apply the count
# during query evaluation (SUM(x * cnt)). State is one row per live fact id:
#   crown_fact_ids(id, cdc_last_update_date, cnt)
# never the full 35-column fact_t_cw. It is maintained with three per-branch
# rules that recompute (id, cdc, cnt) for the affected ids from the crown state:
# cnt = task-count (approval), mes-count (send), DISTINCT-tic-count per
# application_code (countersign) — a per-key count lookup, no fan-out.


def _fid_branch_selects(pc, id_filter=""):
    """Per-branch SELECT of (id, cdc, cnt) over the alive inst-core. id_filter
    optionally restricts to a set of application_inst_ids (incremental case)."""
    base = (f"FROM crown_vs_oa oa\n"
            f"JOIN {pc}cfs_opt_application_inst_t opii"
            f" ON opii.operator_application_id = oa.operator_application_id")
    idcdc = ("opii.application_inst_id AS id,"
             " GREATEST(oa.cdc_last_update_date, opii.cdc_last_update_date) AS cdc_last_update_date")
    return [
        f"""SELECT {idcdc}, GREATEST(1, COALESCE(tk.c, 0)) AS cnt
{base}
LEFT JOIN (SELECT proc_inst_id, COUNT(*) c FROM {pc}cfs_proc_task_t GROUP BY proc_inst_id) tk
       ON tk.proc_inst_id = oa.work_flow_id
WHERE oa.status = 30 AND oa.flag_opii{id_filter}""",
        f"""SELECT {idcdc}, GREATEST(1, (SELECT COUNT(*) FROM crown_mes)) AS cnt
{base}
WHERE oa.status = 40 AND oa.flag_opii AND oa.flag_temp{id_filter}""",
        f"""SELECT {idcdc}, COALESCE(ti.c, 0) AS cnt
{base}
LEFT JOIN (SELECT application_code, COUNT(*) c FROM crown_vp_tic GROUP BY application_code) ti
       ON ti.application_code = oa.application_code
WHERE oa.status = 50 AND oa.flag_opii AND oa.flag_tic{id_filter}""",
    ]


def fact_ids_init_sql(dialect):
    """Initial population: distinct live fact ids with cdc and fan-out count."""
    pc = "s000_cqrs_cfs." if dialect == "duckdb" else ""
    return "CREATE TABLE crown_fact_ids AS\n" + "\nUNION ALL\n".join(_fid_branch_selects(pc)) + ";"


def fact_ids_maintain_sql(dialect):
    """Three-rule incremental maintenance of crown_fact_ids (derivation
    counting). Run after the crown state maintenance; reads this step's deltas."""
    dd = dialect == "duckdb"
    ins = "_ins_" if dd else "mlog_ins_"
    dl = "_del_" if dd else "mlog_del_"
    pc = "s000_cqrs_cfs." if dd else ""

    def mk(name, body):
        if dd:
            return f"CREATE OR REPLACE TEMP TABLE {name} AS {body};"
        return f"DROP TABLE IF EXISTS {name};\nCREATE TEMP TABLE {name} AS {body};"

    p = []
    w = p.append
    # application_codes touched this step (affect tic / temp counts)
    w(mk("_fi_codes", f"""SELECT DISTINCT application_code FROM (
  SELECT application_code FROM {ins}cinv UNION ALL SELECT application_code FROM {dl}cinv
  UNION ALL SELECT application_code FROM {ins}inv UNION ALL SELECT application_code FROM {dl}inv) u"""))
    # work-flow proc_inst_ids touched this step (affect approval task count)
    w(mk("_fi_wf", f"""SELECT DISTINCT proc_inst_id FROM (
  SELECT proc_inst_id FROM {ins}task UNION ALL SELECT proc_inst_id FROM {dl}task
  UNION ALL SELECT t.proc_inst_id FROM {pc}cfs_proc_task_t t
    WHERE t.route_id IN (SELECT route_id FROM {ins}route UNION ALL SELECT route_id FROM {dl}route)) u"""))
    # affected oa: changed directly, or via code (tic/temp), work_flow (task),
    # or a change to the mes singleton (which scales the send count)
    w(mk("_fi_oa", f"""SELECT DISTINCT operator_application_id FROM (
  SELECT operator_application_id FROM {ins}app UNION ALL SELECT operator_application_id FROM {dl}app
  UNION ALL SELECT operator_application_id FROM {ins}inst UNION ALL SELECT operator_application_id FROM {dl}inst
  UNION ALL SELECT operator_application_id FROM crown_vs_oa WHERE application_code IN (SELECT application_code FROM _fi_codes)
  UNION ALL SELECT operator_application_id FROM crown_vs_oa WHERE work_flow_id IN (SELECT proc_inst_id FROM _fi_wf)
  UNION ALL SELECT operator_application_id FROM crown_vs_oa WHERE status = 40 AND EXISTS (
      SELECT 1 FROM {ins}msg WHERE app_name='cfs' AND language='zh_CN' AND message_key='{MSG_KEY}'
      UNION ALL SELECT 1 FROM {dl}msg WHERE app_name='cfs' AND language='zh_CN' AND message_key='{MSG_KEY}')) u"""))
    # affected fact ids = application_inst_ids of affected oa's, plus changed opii
    w(mk("_fi_ids", f"""SELECT DISTINCT id FROM (
  SELECT application_inst_id AS id FROM {pc}cfs_opt_application_inst_t
    WHERE operator_application_id IN (SELECT operator_application_id FROM _fi_oa)
  UNION ALL SELECT application_inst_id FROM {ins}inst
  UNION ALL SELECT application_inst_id FROM {dl}inst) u"""))
    # three rules: drop the affected ids, then re-derive (id, cdc, cnt) per branch
    w("DELETE FROM crown_fact_ids WHERE id IN (SELECT id FROM _fi_ids);")
    idf = " AND opii.application_inst_id IN (SELECT id FROM _fi_ids)"
    for sel in _fid_branch_selects(pc, idf):
        w(f"INSERT INTO crown_fact_ids\n{sel};")
    for t in ("_fi_codes", "_fi_wf", "_fi_oa", "_fi_ids"):
        w(f"DROP TABLE IF EXISTS {t};")
    return "\n".join(p)


# ==========================================================================
# COUNT queries by aggregation over partial counts (no full-join materialize)
# ==========================================================================
#
# For a COUNT of a join, CROWN does not build the join and count the rows; it
# combines the partial counts (annotations) already maintained on each
# relation. For this workload:
#   * q1 (detail live): sum over the inst-core (oa x opii, filtered by
#       watermark, non-OEM contract, and a salesperson-region semi-join/factor)
#       of a per-key branch multiplier -- task-count for approval, mes-count
#       for send, DISTINCT-tic-count per application_code for countersign. The
#       n:m tic fan-out and the 1:n task fan-out become a single multiply by a
#       maintained per-key count, so no join rows are ever materialized.
#   * q3 (summary live): its scope (fact ids passing the watermark) is the
#       inst-core id set -- id and cdc are available before any branch fan-out
#       -- so the fact assembly is not needed; the group-count still runs over
#       the (materialized, method-independent) detail output table.
#   * q2 (detail tombstone): "is id still live in branch B" is decided from the
#       inst-core (branch alive, not logically deleted), not the branch view.
#   * q4 (summary tombstone): reads only the output tables; no fact assembly
#       (handled generically by the runner).
#
# Verified equal to the naive full-join count (and hence to recompute) at every
# step of every scenario.

def crown_count_sql(dialect, qname, dtl):
    """Return `SELECT COUNT(*) AS cnt ...` for q1/q2/q3 of the crown method.
    dtl is the detail output table name (q2/q3). Base tables are bare on
    openGauss (search_path) and schema-qualified on DuckDB. q4 is not handled
    here (it reads only output tables)."""
    dd = dialect == "duckdb"
    pc = "s000_cqrs_cfs." if dd else ""            # cqrs schema prefix
    pd = "s000_dwt_hws_iao." if dd else ""         # dwt schema prefix
    iv = "INTERVAL 30 MINUTE" if dd else "INTERVAL '30 minute'"

    def delfalse(oa, op):
        if dd:
            return (f"NOT (GREATEST(CAST({oa}.logical_is_deleted AS INTEGER),"
                    f"CAST({op}.logical_is_deleted AS INTEGER))::BOOLEAN)")
        return f"greatest({oa}.logical_is_deleted, {op}.logical_is_deleted) = false"

    wm = (f"(SELECT job_last_start_date - {iv} FROM {pd}dwd_job_status_t_05 LIMIT 1)")
    alive = ("oa.flag_opii AND (oa.status = 30 OR (oa.status = 40 AND oa.flag_temp)"
             " OR (oa.status = 50 AND oa.flag_tic))")

    if qname == "q1":
        return f"""SELECT COALESCE(SUM(
  (CASE oa.status
     WHEN 30 THEN GREATEST(1, COALESCE(tk.c, 0))
     WHEN 40 THEN GREATEST(1, mes_c.c)
     WHEN 50 THEN COALESCE(ti.c, 0)
   END)
  *
  (CASE WHEN COALESCE(s1.c, 0) = 0 AND COALESCE(s2.c, 0) = 0 THEN 0
        ELSE GREATEST(COALESCE(s1.c, 0), 1) * GREATEST(COALESCE(s2.c, 0), 1) END)
), 0) AS cnt
FROM crown_vs_oa oa
JOIN {pc}cfs_opt_application_inst_t opii ON opii.operator_application_id = oa.operator_application_id
LEFT JOIN {pc}cfs_cfg_company_t comp ON comp.company_id = oa.company_id
LEFT JOIN (SELECT application_code, COUNT(*) c FROM crown_vp_tic GROUP BY application_code) ti
       ON oa.status = 50 AND ti.application_code = oa.application_code
LEFT JOIN (SELECT proc_inst_id, COUNT(*) c FROM {pc}cfs_proc_task_t GROUP BY proc_inst_id) tk
       ON oa.status = 30 AND tk.proc_inst_id = oa.work_flow_id
LEFT JOIN (SELECT salesperson_id, COUNT(*) c FROM {pd}cfs_salesperson_region_t
           WHERE source_code = '业务补录' GROUP BY salesperson_id) s1
       ON s1.salesperson_id = oa.salesperson_id
LEFT JOIN (SELECT salesperson_id, unit_code, COUNT(*) c FROM {pd}cfs_salesperson_region_t
           WHERE source_code = '原始表中已有的账套' GROUP BY salesperson_id, unit_code) s2
       ON s2.salesperson_id = oa.salesperson_id AND s2.unit_code = comp.company_code
CROSS JOIN (SELECT COUNT(*) c FROM crown_mes) mes_c
WHERE {alive}
  AND opii.contract_id IN (SELECT contract_id FROM {pd}cfs_comm_contract_t
                           WHERE hw_contract_bussource_code <> 'OEM' OR hw_contract_bussource_code IS NULL)
  AND GREATEST(oa.cdc_last_update_date, opii.cdc_last_update_date) >= {wm};"""

    if qname == "q2":
        def branch(status, extra):
            return (f"SELECT 1 FROM {pc}cfs_opt_application_inst_t opii"
                    f" JOIN crown_vs_oa oa ON oa.operator_application_id = opii.operator_application_id"
                    f" WHERE oa.status = {status} AND oa.flag_opii{extra}"
                    f" AND {delfalse('oa','opii')} AND opii.application_inst_id = fact_t.id")
        return f"""SELECT COUNT(*) AS cnt FROM (
  SELECT 1 FROM {dtl} fact_t
  WHERE (fact_t.node_type = '待审批' AND NOT EXISTS ({branch(30, '')}))
     OR (fact_t.node_type = '待寄送' AND NOT EXISTS ({branch(40, ' AND oa.flag_temp')}))
     OR (fact_t.node_type = '待签返' AND NOT EXISTS ({branch(50, ' AND oa.flag_tic')}))
) q;"""

    # q3 is not handled here: it routes through the generic q3 builder with
    # its fact scope table (fact_t_cw) replaced by the maintained crown_fact_ids.
    raise ValueError(qname)


def crown_q3_rebind(sql, count_form=False):
    """Point the generic q3 scope at the maintained id view instead of
    assembling fact_t_cw. For the count form the group set is unchanged, so we
    just swap the table (distinct ids). For the row-producing build we carry the
    fan-out count from the view and weight the SUM aggregates by it, so a single
    (distinct) join reproduces the multiset SUMs (MAX and DISTINCT string_agg
    are multiplicity-invariant; other string_aggs are excluded from checks)."""
    if count_form:
        return sql.replace("fact_t_cw", "crown_fact_ids")
    sql = sql.replace("fact_t.id\n    FROM fact_t_cw AS fact_t",
                      "fact_t.id, fact_t.cnt\n    FROM crown_fact_ids AS fact_t")
    for col in ("usd_total_amount", "rmb_total_amount", "total_amount", "con_mi_qty"):
        sql = sql.replace(f"SUM(t.{col})", f"SUM(t.{col} * scp.cnt)")
    return sql.replace("fact_t_cw", "crown_fact_ids")  # safety for any remainder


def _crown_view_rebind(sql, base_ref):
    """Rebind the assembly-view FROM sources onto the maintained partial
    results. `base_ref('t')` returns the qualified name of base table t in the
    target dialect (schema-qualified on DuckDB, bare on openGauss)."""
    oa = base_ref("cfs_opt_application_t")
    opii = base_ref("cfs_opt_application_inst_t")
    mes = base_ref("tpl_fd_message_t")
    sql = sql.replace(
        f"FROM {oa} oa\nJOIN {opii} opii",
        "FROM (SELECT * FROM crown_vs_oa\n"
        "      WHERE flag_opii AND (status = 30 OR (status = 40 AND flag_temp)\n"
        "                                       OR (status = 50 AND flag_tic))) oa\n"
        f"JOIN {opii} opii")
    sql = sql.replace("LEFT JOIN apt_mv apt",
                      "LEFT JOIN (SELECT application_code, max_tax_invoice_date AS tax_invoice_date"
                      " FROM crown_agg_apt) apt")
    sql = sql.replace("JOIN temp_mv temp",
                      "JOIN (SELECT application_code, max_approve_date AS approve_date"
                      " FROM crown_agg_temp) temp")
    sql = sql.replace("JOIN tic_mv tic",
                      "JOIN (SELECT invoice_no, application_code, send_date"
                      " FROM crown_vp_tic) tic")
    import re
    sql = re.sub(r"LEFT JOIN " + re.escape(mes) + r" mes\s*"
                 r"ON mes\.app_name = 'cfs' AND mes\.language = 'zh_CN'\s*"
                 r"AND mes\.message_key = '" + re.escape(MSG_KEY) + r"'",
                 "LEFT JOIN crown_mes mes ON (true)", sql)
    for name in MV_NAMES:
        sql = sql.replace(name, name.replace("_mv", "_cw"))
    return sql


# ==========================================================================
# DuckDB
# ==========================================================================

def duckdb_state_init_sql():
    return f"""
CREATE TABLE crown_src_ccci AS
SELECT {CCCI_COLS}
FROM s000_cqrs_cfs.cfs_cinv_customer_invoice_t WHERE status >= 3;

CREATE TABLE crown_src_cici AS
SELECT invoice_id, application_code, approve_date, status,
       tax_invoice_no AS invoice_no, send_date
FROM s000_cqrs_cfs.cfs_inv_invoice_info_t WHERE status IN (30, 40);

CREATE TABLE crown_agg_apt AS
SELECT application_code, MAX(tax_invoice_date) AS max_tax_invoice_date,
       COUNT(*) AS cnt, COUNT(tax_invoice_date) AS cnt_nonnull
FROM crown_src_ccci GROUP BY application_code;

CREATE TABLE crown_agg_temp AS
SELECT application_code, MAX(approve_date) AS max_approve_date,
       COUNT(*) AS cnt, COUNT(approve_date) AS cnt_nonnull
FROM (SELECT application_code, approve_date FROM crown_src_ccci WHERE status = 30
      UNION ALL
      SELECT application_code, approve_date FROM crown_src_cici WHERE status = 30)
GROUP BY application_code;

CREATE TABLE crown_vp_tic AS
SELECT invoice_no, application_code, send_date, COUNT(*) AS cnt
FROM (SELECT invoice_no, application_code, send_date FROM crown_src_ccci
      WHERE status >= 40 AND (office_receive_date IS NULL OR customer_receive_date IS NULL)
      UNION ALL
      SELECT invoice_no, application_code, send_date FROM crown_src_cici
      WHERE status >= 40)
GROUP BY invoice_no, application_code, send_date;

CREATE TABLE crown_vp_opii AS
SELECT operator_application_id, COUNT(*) AS cnt
FROM s000_cqrs_cfs.cfs_opt_application_inst_t GROUP BY operator_application_id;

CREATE TABLE crown_vs_oa AS
SELECT {_oa_cols()},
       EXISTS (SELECT 1 FROM crown_vp_opii p
               WHERE p.operator_application_id = oa.operator_application_id) AS flag_opii,
       EXISTS (SELECT 1 FROM crown_agg_temp g
               WHERE g.application_code = oa.application_code) AS flag_temp,
       EXISTS (SELECT 1 FROM crown_vp_tic v
               WHERE v.application_code = oa.application_code) AS flag_tic
FROM s000_cqrs_cfs.cfs_opt_application_t oa
WHERE oa.{OA_FILTER.replace(' AND ', ' AND oa.')};

CREATE TABLE crown_mes AS
SELECT message_id, message FROM s000_cqrs_cfs.tpl_fd_message_t
WHERE app_name = 'cfs' AND language = 'zh_CN' AND message_key = '{MSG_KEY}';
"""


def duckdb_assembly_views_sql(lv_init_text):
    """Build the *_cw assembly views from the logical_views/init.sql text."""
    return _crown_view_rebind(lv_init_text, lambda t: f"s000_cqrs_cfs.{t}")


def duckdb_maintain_sql():
    return f"""
-- (1) sources: R-Update with selection at update time; old rows recovered from state
CREATE OR REPLACE TEMP TABLE _c_dsrc_ccci AS
SELECT s.*, -1 AS w FROM crown_src_ccci s
WHERE s.customer_invoice_id IN (SELECT customer_invoice_id FROM _del_cinv)
UNION ALL
SELECT {CCCI_COLS}, +1 FROM _ins_cinv WHERE status >= 3;

CREATE OR REPLACE TEMP TABLE _c_dsrc_cici AS
SELECT s.*, -1 AS w FROM crown_src_cici s
WHERE s.invoice_id IN (SELECT invoice_id FROM _del_inv)
UNION ALL
SELECT invoice_id, application_code, approve_date, status, tax_invoice_no, send_date, +1
FROM _ins_inv WHERE status IN (30, 40);

DELETE FROM crown_src_ccci WHERE customer_invoice_id IN (SELECT customer_invoice_id FROM _del_cinv);
INSERT INTO crown_src_ccci SELECT * EXCLUDE (w) FROM _c_dsrc_ccci WHERE w = 1;
DELETE FROM crown_src_cici WHERE invoice_id IN (SELECT invoice_id FROM _del_inv);
INSERT INTO crown_src_cici SELECT * EXCLUDE (w) FROM _c_dsrc_cici WHERE w = 1;

-- (2) MAX aggregates (P-Update with annotations; extension: recalc on delete)
CREATE OR REPLACE TEMP TABLE _c_d_apt AS
SELECT application_code,
       SUM(w) AS cnt_d,
       SUM(CASE WHEN tax_invoice_date IS NOT NULL THEN w ELSE 0 END) AS nn_d,
       MAX(CASE WHEN w = 1 THEN tax_invoice_date END) AS ins_max,
       MAX(CASE WHEN w = -1 THEN tax_invoice_date END) AS del_max
FROM _c_dsrc_ccci GROUP BY application_code;

MERGE INTO crown_agg_apt t USING _c_d_apt d ON t.application_code = d.application_code
WHEN MATCHED THEN UPDATE SET
    cnt = t.cnt + d.cnt_d, cnt_nonnull = t.cnt_nonnull + d.nn_d,
    max_tax_invoice_date = CASE WHEN d.ins_max IS NULL THEN t.max_tax_invoice_date
        WHEN t.max_tax_invoice_date IS NULL OR d.ins_max > t.max_tax_invoice_date
        THEN d.ins_max ELSE t.max_tax_invoice_date END
WHEN NOT MATCHED THEN INSERT VALUES (d.application_code, d.ins_max, d.cnt_d, d.nn_d);

UPDATE crown_agg_apt t
SET max_tax_invoice_date = (SELECT MAX(s.tax_invoice_date) FROM crown_src_ccci s
                            WHERE s.application_code = t.application_code)
WHERE t.cnt > 0 AND t.application_code IN (
    SELECT d.application_code FROM _c_d_apt d
    JOIN crown_agg_apt x ON x.application_code = d.application_code
    WHERE d.del_max IS NOT NULL
      AND (x.max_tax_invoice_date IS NULL OR d.del_max >= x.max_tax_invoice_date));
DELETE FROM crown_agg_apt WHERE cnt <= 0;
UPDATE crown_agg_apt SET max_tax_invoice_date = NULL WHERE cnt_nonnull = 0;

CREATE OR REPLACE TEMP TABLE _c_d_temp AS
SELECT application_code,
       SUM(w) AS cnt_d,
       SUM(CASE WHEN approve_date IS NOT NULL THEN w ELSE 0 END) AS nn_d,
       MAX(CASE WHEN w = 1 THEN approve_date END) AS ins_max,
       MAX(CASE WHEN w = -1 THEN approve_date END) AS del_max
FROM (SELECT application_code, approve_date, w FROM _c_dsrc_ccci WHERE status = 30
      UNION ALL
      SELECT application_code, approve_date, w FROM _c_dsrc_cici WHERE status = 30)
GROUP BY application_code;

-- pre-state snapshot restricted to this step's delta keys (S-Update input)
CREATE OR REPLACE TEMP TABLE _c_pre_temp AS
SELECT application_code FROM crown_agg_temp
WHERE application_code IN (SELECT application_code FROM _c_d_temp);

MERGE INTO crown_agg_temp t USING _c_d_temp d ON t.application_code = d.application_code
WHEN MATCHED THEN UPDATE SET
    cnt = t.cnt + d.cnt_d, cnt_nonnull = t.cnt_nonnull + d.nn_d,
    max_approve_date = CASE WHEN d.ins_max IS NULL THEN t.max_approve_date
        WHEN t.max_approve_date IS NULL OR d.ins_max > t.max_approve_date
        THEN d.ins_max ELSE t.max_approve_date END
WHEN NOT MATCHED THEN INSERT VALUES (d.application_code, d.ins_max, d.cnt_d, d.nn_d);

UPDATE crown_agg_temp t
SET max_approve_date = (
    SELECT MAX(approve_date) FROM (
        SELECT approve_date FROM crown_src_ccci s
        WHERE s.application_code = t.application_code AND s.status = 30
        UNION ALL
        SELECT approve_date FROM crown_src_cici s
        WHERE s.application_code = t.application_code AND s.status = 30))
WHERE t.cnt > 0 AND t.application_code IN (
    SELECT d.application_code FROM _c_d_temp d
    JOIN crown_agg_temp x ON x.application_code = d.application_code
    WHERE d.del_max IS NOT NULL
      AND (x.max_approve_date IS NULL OR d.del_max >= x.max_approve_date));
DELETE FROM crown_agg_temp WHERE cnt <= 0;
UPDATE crown_agg_temp SET max_approve_date = NULL WHERE cnt_nonnull = 0;

CREATE OR REPLACE TEMP TABLE _c_post_temp AS
SELECT application_code FROM crown_agg_temp
WHERE application_code IN (SELECT application_code FROM _c_d_temp);

-- (3) DISTINCT projection (P-Update, derivation counting)
CREATE OR REPLACE TEMP TABLE _c_d_tic AS
SELECT invoice_no, application_code, send_date, SUM(w) AS w
FROM (SELECT invoice_no, application_code, send_date, w FROM _c_dsrc_ccci
      WHERE status >= 40 AND (office_receive_date IS NULL OR customer_receive_date IS NULL)
      UNION ALL
      SELECT invoice_no, application_code, send_date, w FROM _c_dsrc_cici
      WHERE status >= 40)
GROUP BY invoice_no, application_code, send_date;

CREATE OR REPLACE TEMP TABLE _c_pre_tic AS
SELECT DISTINCT application_code FROM crown_vp_tic
WHERE application_code IN (SELECT DISTINCT application_code FROM _c_d_tic);

MERGE INTO crown_vp_tic t USING _c_d_tic d
    ON t.invoice_no IS NOT DISTINCT FROM d.invoice_no
   AND t.application_code IS NOT DISTINCT FROM d.application_code
   AND t.send_date IS NOT DISTINCT FROM d.send_date
WHEN MATCHED THEN UPDATE SET cnt = t.cnt + d.w
WHEN NOT MATCHED THEN INSERT VALUES (d.invoice_no, d.application_code, d.send_date, d.w);
DELETE FROM crown_vp_tic WHERE cnt <= 0;

CREATE OR REPLACE TEMP TABLE _c_post_tic AS
SELECT DISTINCT application_code FROM crown_vp_tic
WHERE application_code IN (SELECT DISTINCT application_code FROM _c_d_tic);

-- (4) V_p(opii): projection with derivation counting (old rows = staged delta)
CREATE OR REPLACE TEMP TABLE _c_d_opii AS
SELECT operator_application_id, SUM(w) AS w
FROM (SELECT operator_application_id, -1 AS w FROM _del_inst
      UNION ALL
      SELECT operator_application_id, +1 FROM _ins_inst)
GROUP BY operator_application_id;

CREATE OR REPLACE TEMP TABLE _c_pre_opii AS
SELECT operator_application_id FROM crown_vp_opii
WHERE operator_application_id IN (SELECT operator_application_id FROM _c_d_opii);

MERGE INTO crown_vp_opii t USING _c_d_opii d ON t.operator_application_id = d.operator_application_id
WHEN MATCHED THEN UPDATE SET cnt = t.cnt + d.w
WHEN NOT MATCHED THEN INSERT VALUES (d.operator_application_id, d.w);
DELETE FROM crown_vp_opii WHERE cnt <= 0;

CREATE OR REPLACE TEMP TABLE _c_post_opii AS
SELECT operator_application_id FROM crown_vp_opii
WHERE operator_application_id IN (SELECT operator_application_id FROM _c_d_opii);

-- (5) S-Update: liveness transitions (born/died among delta keys) -> V_s(oa) flags
UPDATE crown_vs_oa SET flag_opii = true
WHERE flag_opii = false AND operator_application_id IN (
    SELECT operator_application_id FROM _c_post_opii
    WHERE operator_application_id NOT IN (SELECT operator_application_id FROM _c_pre_opii));
UPDATE crown_vs_oa SET flag_opii = false
WHERE flag_opii = true AND operator_application_id IN (
    SELECT operator_application_id FROM _c_pre_opii
    WHERE operator_application_id NOT IN (SELECT operator_application_id FROM _c_post_opii));

UPDATE crown_vs_oa SET flag_temp = true
WHERE flag_temp = false AND application_code IN (
    SELECT application_code FROM _c_post_temp
    WHERE application_code NOT IN (SELECT application_code FROM _c_pre_temp));
UPDATE crown_vs_oa SET flag_temp = false
WHERE flag_temp = true AND application_code IN (
    SELECT application_code FROM _c_pre_temp
    WHERE application_code NOT IN (SELECT application_code FROM _c_post_temp));

UPDATE crown_vs_oa SET flag_tic = true
WHERE flag_tic = false AND application_code IN (
    SELECT application_code FROM _c_post_tic
    WHERE application_code NOT IN (SELECT application_code FROM _c_pre_tic));
UPDATE crown_vs_oa SET flag_tic = false
WHERE flag_tic = true AND application_code IN (
    SELECT application_code FROM _c_pre_tic
    WHERE application_code NOT IN (SELECT application_code FROM _c_post_tic));

-- (6) R-Update on oa
DELETE FROM crown_vs_oa WHERE operator_application_id IN
    (SELECT operator_application_id FROM _del_app);
INSERT INTO crown_vs_oa
SELECT {_oa_cols()},
       EXISTS (SELECT 1 FROM crown_vp_opii p
               WHERE p.operator_application_id = oa.operator_application_id),
       EXISTS (SELECT 1 FROM crown_agg_temp g
               WHERE g.application_code = oa.application_code),
       EXISTS (SELECT 1 FROM crown_vp_tic v
               WHERE v.application_code = oa.application_code)
FROM _ins_app oa
WHERE oa.{OA_FILTER.replace(' AND ', ' AND oa.')};

-- (7) mes singleton
DELETE FROM crown_mes WHERE message_id IN (SELECT message_id FROM _del_msg);
INSERT INTO crown_mes SELECT message_id, message FROM _ins_msg
WHERE app_name = 'cfs' AND language = 'zh_CN' AND message_key = '{MSG_KEY}';

DROP TABLE IF EXISTS _c_dsrc_ccci; DROP TABLE IF EXISTS _c_dsrc_cici;
DROP TABLE IF EXISTS _c_d_apt; DROP TABLE IF EXISTS _c_d_temp;
DROP TABLE IF EXISTS _c_pre_temp; DROP TABLE IF EXISTS _c_post_temp;
DROP TABLE IF EXISTS _c_d_tic; DROP TABLE IF EXISTS _c_pre_tic;
DROP TABLE IF EXISTS _c_post_tic; DROP TABLE IF EXISTS _c_d_opii;
DROP TABLE IF EXISTS _c_pre_opii; DROP TABLE IF EXISTS _c_post_opii;
"""


# ==========================================================================
# openGauss
# ==========================================================================

# state indexes: counterpart of the ivm method's matview indexes (build time
# reported the same way; the maintenance logic guarantees the identities).
OG_INDEX_DDL = [
    "CREATE INDEX cw_src_ccci_pk ON {s}.crown_src_ccci (customer_invoice_id)",
    "CREATE INDEX cw_src_ccci_code ON {s}.crown_src_ccci (application_code)",
    "CREATE INDEX cw_src_cici_pk ON {s}.crown_src_cici (invoice_id)",
    "CREATE INDEX cw_src_cici_code ON {s}.crown_src_cici (application_code)",
    "CREATE INDEX cw_agg_apt_code ON {s}.crown_agg_apt (application_code)",
    "CREATE INDEX cw_agg_temp_code ON {s}.crown_agg_temp (application_code)",
    "CREATE INDEX cw_vp_tic_code ON {s}.crown_vp_tic (application_code)",
    "CREATE INDEX cw_vp_opii_key ON {s}.crown_vp_opii (operator_application_id)",
    "CREATE INDEX cw_vs_oa_pk ON {s}.crown_vs_oa (operator_application_id)",
    "CREATE INDEX cw_vs_oa_code ON {s}.crown_vs_oa (application_code)",
    "CREATE INDEX cw_vs_oa_wf ON {s}.crown_vs_oa (work_flow_id)",
]


def opengauss_state_init_sql():
    """Bare names; the caller sets search_path to the scenario schema first."""
    return f"""
CREATE TABLE crown_src_ccci AS
SELECT {CCCI_COLS}
FROM cfs_cinv_customer_invoice_t WHERE status >= 3;

CREATE TABLE crown_src_cici AS
SELECT invoice_id, application_code, approve_date, status,
       tax_invoice_no AS invoice_no, send_date
FROM cfs_inv_invoice_info_t WHERE status IN (30, 40);

CREATE TABLE crown_agg_apt AS
SELECT application_code, MAX(tax_invoice_date) AS max_tax_invoice_date,
       COUNT(*) AS cnt, COUNT(tax_invoice_date) AS cnt_nonnull
FROM crown_src_ccci GROUP BY application_code;

CREATE TABLE crown_agg_temp AS
SELECT application_code, MAX(approve_date) AS max_approve_date,
       COUNT(*) AS cnt, COUNT(approve_date) AS cnt_nonnull
FROM (SELECT application_code, approve_date FROM crown_src_ccci WHERE status = 30
      UNION ALL
      SELECT application_code, approve_date FROM crown_src_cici WHERE status = 30) u
GROUP BY application_code;

CREATE TABLE crown_vp_tic AS
SELECT invoice_no, application_code, send_date, COUNT(*) AS cnt
FROM (SELECT invoice_no, application_code, send_date FROM crown_src_ccci
      WHERE status >= 40 AND (office_receive_date IS NULL OR customer_receive_date IS NULL)
      UNION ALL
      SELECT invoice_no, application_code, send_date FROM crown_src_cici
      WHERE status >= 40) u
GROUP BY invoice_no, application_code, send_date;

CREATE TABLE crown_vp_opii AS
SELECT operator_application_id, COUNT(*) AS cnt
FROM cfs_opt_application_inst_t GROUP BY operator_application_id;

CREATE TABLE crown_vs_oa AS
SELECT {_oa_cols()},
       (p.operator_application_id IS NOT NULL) AS flag_opii,
       (g.application_code IS NOT NULL) AS flag_temp,
       (v.application_code IS NOT NULL) AS flag_tic
FROM cfs_opt_application_t oa
LEFT JOIN crown_vp_opii p ON p.operator_application_id = oa.operator_application_id
LEFT JOIN (SELECT DISTINCT application_code FROM crown_agg_temp) g
       ON g.application_code = oa.application_code
LEFT JOIN (SELECT DISTINCT application_code FROM crown_vp_tic) v
       ON v.application_code = oa.application_code
WHERE oa.{OA_FILTER.replace(' AND ', ' AND oa.')};

CREATE TABLE crown_mes AS
SELECT message_id, message FROM tpl_fd_message_t
WHERE app_name = 'cfs' AND language = 'zh_CN' AND message_key = '{MSG_KEY}';
"""


def opengauss_index_sql(schema):
    return ";\n".join(d.format(s=schema) for d in OG_INDEX_DDL) + ";"


def opengauss_assembly_views_sql(lv_init_text, schema):
    """Build the *_cw assembly views from the logical_views/init.sql text
    (still using s000_* base-table refs), then rebind s000_* -> schema."""
    sql = _crown_view_rebind(lv_init_text, lambda t: f"s000_cqrs_cfs.{t}")
    sql = sql.replace("s000_cqrs_cfs.", f"{schema}.").replace("s000_dwt_hws_iao.", f"{schema}.")
    return sql


def _tt(name, body):
    return f"DROP TABLE IF EXISTS {name};\nCREATE TEMP TABLE {name} AS {body};"


def opengauss_maintain_sql():
    """Bare names / mlog_* deltas; the caller sets search_path first."""
    p = []
    w = p.append

    # (1) sources: R-Update with selection at update time; old rows from state
    w(_tt("_c_dsrc_ccci", f"""
SELECT s.*, -1 AS w FROM crown_src_ccci s
WHERE s.customer_invoice_id IN (SELECT customer_invoice_id FROM mlog_del_cinv)
UNION ALL
SELECT {CCCI_COLS}, 1 FROM mlog_ins_cinv WHERE status >= 3"""))
    w(_tt("_c_dsrc_cici", """
SELECT s.*, -1 AS w FROM crown_src_cici s
WHERE s.invoice_id IN (SELECT invoice_id FROM mlog_del_inv)
UNION ALL
SELECT invoice_id, application_code, approve_date, status, tax_invoice_no, send_date, 1
FROM mlog_ins_inv WHERE status IN (30, 40)"""))
    w("DELETE FROM crown_src_ccci WHERE customer_invoice_id IN (SELECT customer_invoice_id FROM mlog_del_cinv);")
    w(f"INSERT INTO crown_src_ccci SELECT {CCCI_COLS} FROM _c_dsrc_ccci WHERE w = 1;")
    w("DELETE FROM crown_src_cici WHERE invoice_id IN (SELECT invoice_id FROM mlog_del_inv);")
    w("INSERT INTO crown_src_cici SELECT invoice_id, application_code, approve_date, status, invoice_no, send_date FROM _c_dsrc_cici WHERE w = 1;")

    # (2) MAX aggregates (P-Update with annotations; extension: recalc on delete)
    for agg, dsrc, val, maxcol in (
            ("crown_agg_apt", "_c_dsrc_ccci", "tax_invoice_date", "max_tax_invoice_date"),
            ("crown_agg_temp", "(SELECT application_code, approve_date, w FROM _c_dsrc_ccci WHERE status = 30"
             " UNION ALL SELECT application_code, approve_date, w FROM _c_dsrc_cici WHERE status = 30) u",
             "approve_date", "max_approve_date")):
        d = "_c_d_apt" if agg == "crown_agg_apt" else "_c_d_temp"
        w(_tt(d, f"""
SELECT application_code,
       SUM(w) AS cnt_d,
       SUM(CASE WHEN {val} IS NOT NULL THEN w ELSE 0 END) AS nn_d,
       MAX(CASE WHEN w = 1 THEN {val} END) AS ins_max,
       MAX(CASE WHEN w = -1 THEN {val} END) AS del_max
FROM {dsrc} GROUP BY application_code"""))
        if agg == "crown_agg_temp":
            w(_tt("_c_pre_temp", f"""
SELECT application_code FROM crown_agg_temp
WHERE application_code IN (SELECT application_code FROM {d})"""))
        w(f"""UPDATE {agg} SET
    cnt = {agg}.cnt + d.cnt_d, cnt_nonnull = {agg}.cnt_nonnull + d.nn_d,
    {maxcol} = CASE WHEN d.ins_max IS NULL THEN {agg}.{maxcol}
        WHEN {agg}.{maxcol} IS NULL OR d.ins_max > {agg}.{maxcol}
        THEN d.ins_max ELSE {agg}.{maxcol} END
FROM {d} d WHERE {agg}.application_code = d.application_code;""")
        w(f"""INSERT INTO {agg}
SELECT d.application_code, d.ins_max, d.cnt_d, d.nn_d FROM {d} d
WHERE NOT EXISTS (SELECT 1 FROM {agg} t WHERE t.application_code = d.application_code);""")
        w(_tt(f"_c_sus{d}", f"""
SELECT d.application_code AS c FROM {d} d
JOIN {agg} x ON x.application_code = d.application_code
WHERE d.del_max IS NOT NULL
  AND (x.{maxcol} IS NULL OR d.del_max >= x.{maxcol})"""))
        recalc_src = ("crown_src_ccci s WHERE s.application_code IN (SELECT c FROM _c_sus" + d + ")"
                      if agg == "crown_agg_apt" else
                      "(SELECT application_code, approve_date FROM crown_src_ccci WHERE status = 30"
                      " UNION ALL SELECT application_code, approve_date FROM crown_src_cici WHERE status = 30) s"
                      " WHERE s.application_code IN (SELECT c FROM _c_sus" + d + ")")
        w(f"""UPDATE {agg} SET {maxcol} = r.mx
FROM (SELECT s.application_code AS c, MAX(s.{val}) AS mx
      FROM {recalc_src}
      GROUP BY s.application_code) r
WHERE {agg}.application_code = r.c AND {agg}.cnt > 0;""")
        w(f"DELETE FROM {agg} WHERE cnt <= 0;")
        w(f"UPDATE {agg} SET {maxcol} = NULL WHERE cnt_nonnull = 0;")
        if agg == "crown_agg_temp":
            w(_tt("_c_post_temp", f"""
SELECT application_code FROM crown_agg_temp
WHERE application_code IN (SELECT application_code FROM {d})"""))

    # (3) DISTINCT projection (P-Update, derivation counting)
    w(_tt("_c_d_tic", """
SELECT invoice_no, application_code, send_date, SUM(w) AS w
FROM (SELECT invoice_no, application_code, send_date, w FROM _c_dsrc_ccci
      WHERE status >= 40 AND (office_receive_date IS NULL OR customer_receive_date IS NULL)
      UNION ALL
      SELECT invoice_no, application_code, send_date, w FROM _c_dsrc_cici
      WHERE status >= 40) u
GROUP BY invoice_no, application_code, send_date"""))
    w(_tt("_c_pre_tic", """
SELECT DISTINCT application_code FROM crown_vp_tic
WHERE application_code IN (SELECT DISTINCT application_code FROM _c_d_tic)"""))
    # application_code by plain equality: it is never NULL in this workload, and
    # equality lets the planner use the code index / hash joins — the pure
    # all-IS-NOT-DISTINCT form is neither indexable nor hashable in openGauss
    # and degenerates to a nested loop over the whole projection view.
    nsafe = ("{t}.application_code = d.application_code "
             "AND {t}.invoice_no IS NOT DISTINCT FROM d.invoice_no "
             "AND {t}.send_date IS NOT DISTINCT FROM d.send_date")
    w(f"""UPDATE crown_vp_tic SET cnt = crown_vp_tic.cnt + d.w
FROM _c_d_tic d WHERE {nsafe.format(t='crown_vp_tic')};""")
    w(f"""INSERT INTO crown_vp_tic
SELECT d.invoice_no, d.application_code, d.send_date, d.w FROM _c_d_tic d
WHERE NOT EXISTS (SELECT 1 FROM crown_vp_tic t WHERE {nsafe.format(t='t')});""")
    w("DELETE FROM crown_vp_tic WHERE cnt <= 0;")
    w(_tt("_c_post_tic", """
SELECT DISTINCT application_code FROM crown_vp_tic
WHERE application_code IN (SELECT DISTINCT application_code FROM _c_d_tic)"""))

    # (4) V_p(opii): projection with derivation counting (old rows = staged delta)
    w(_tt("_c_d_opii", """
SELECT operator_application_id, SUM(w) AS w
FROM (SELECT operator_application_id, -1 AS w FROM mlog_del_inst
      UNION ALL
      SELECT operator_application_id, 1 FROM mlog_ins_inst) u
GROUP BY operator_application_id"""))
    w(_tt("_c_pre_opii", """
SELECT operator_application_id FROM crown_vp_opii
WHERE operator_application_id IN (SELECT operator_application_id FROM _c_d_opii)"""))
    w("""UPDATE crown_vp_opii SET cnt = crown_vp_opii.cnt + d.w
FROM _c_d_opii d WHERE crown_vp_opii.operator_application_id = d.operator_application_id;""")
    w("""INSERT INTO crown_vp_opii
SELECT d.operator_application_id, d.w FROM _c_d_opii d
WHERE NOT EXISTS (SELECT 1 FROM crown_vp_opii t
                  WHERE t.operator_application_id = d.operator_application_id);""")
    w("DELETE FROM crown_vp_opii WHERE cnt <= 0;")
    w(_tt("_c_post_opii", """
SELECT operator_application_id FROM crown_vp_opii
WHERE operator_application_id IN (SELECT operator_application_id FROM _c_d_opii)"""))

    # (5) S-Update: liveness transitions (born/died among delta keys) -> flags.
    # born/died are materialized first: inlining pre/post NOT IN as a nested
    # subquery makes openGauss re-evaluate it as a per-row subplan.
    for flag, key, pre, post in (
            ("flag_opii", "operator_application_id", "_c_pre_opii", "_c_post_opii"),
            ("flag_temp", "application_code", "_c_pre_temp", "_c_post_temp"),
            ("flag_tic", "application_code", "_c_pre_tic", "_c_post_tic")):
        w(_tt(f"_c_born_{flag}", f"SELECT a.{key} FROM {post} a"
              f" WHERE NOT EXISTS (SELECT 1 FROM {pre} b WHERE b.{key} = a.{key})"))
        w(_tt(f"_c_died_{flag}", f"SELECT a.{key} FROM {pre} a"
              f" WHERE NOT EXISTS (SELECT 1 FROM {post} b WHERE b.{key} = a.{key})"))
        w(f"""UPDATE crown_vs_oa SET {flag} = true
WHERE {flag} = false AND {key} IN (SELECT {key} FROM _c_born_{flag});""")
        w(f"""UPDATE crown_vs_oa SET {flag} = false
WHERE {flag} = true AND {key} IN (SELECT {key} FROM _c_died_{flag});""")

    # (6) R-Update on oa
    w("DELETE FROM crown_vs_oa WHERE operator_application_id IN (SELECT operator_application_id FROM mlog_del_app);")
    w(f"""INSERT INTO crown_vs_oa
SELECT {_oa_cols()},
       EXISTS (SELECT 1 FROM crown_vp_opii p
               WHERE p.operator_application_id = oa.operator_application_id),
       EXISTS (SELECT 1 FROM crown_agg_temp g
               WHERE g.application_code = oa.application_code),
       EXISTS (SELECT 1 FROM crown_vp_tic v
               WHERE v.application_code = oa.application_code)
FROM mlog_ins_app oa
WHERE oa.{OA_FILTER.replace(' AND ', ' AND oa.')};""")

    # (7) mes singleton
    w("DELETE FROM crown_mes WHERE message_id IN (SELECT message_id FROM mlog_del_msg);")
    w(f"""INSERT INTO crown_mes SELECT message_id, message FROM mlog_ins_msg
WHERE app_name = 'cfs' AND language = 'zh_CN' AND message_key = '{MSG_KEY}';""")
    return "\n".join(p)
