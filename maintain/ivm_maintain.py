#!/usr/bin/env python3
"""
Faithful translation of job5_ivm.sql maintenance to CSV-delta form,
shared by the DuckDB and openGauss runners.

Mapping (per CLAUDE.md §9):
  MLog rows            -> current step's inserted CSV slices (_ins_*) and the
                          full old rows of the deleted slices (_del_*)
  ctid identity        -> source primary keys (tmp_zx carries src_pk, mirroring
                          the original ccci_ctid/cici_ctid columns)
  refresh_time filter  -> implicit (each step's slices ARE the new delta)
  TIMECAPSULE snapshot -> post-state join with overlap exclusion
                          (Δa⋈B ∪ (A−Δa)⋈Δb)
  _ivm_count           -> kept as-is on apt_mv/temp_mv/tic_mv, with
                          group-local MAX recalculation on deletes

Every statement is driven from the delta or probes matviews/join partners on
keys; the large fact tables (cfs_cinv_customer_invoice_t,
cfs_inv_invoice_info_t) are never scanned during maintenance.
"""

SPECIAL_MSG_KEY = "cfs.html.label.role.operatorInvoiceSender"

DELTA_TABLES = [
    ("cinv", "s000_cqrs_cfs.cfs_cinv_customer_invoice_t"),
    ("inv",  "s000_cqrs_cfs.cfs_inv_invoice_info_t"),
    ("app",  "s000_cqrs_cfs.cfs_opt_application_t"),
    ("inst", "s000_cqrs_cfs.cfs_opt_application_inst_t"),
    ("pu",   "s000_cqrs_cfs.cfs_con_payment_unit_t"),
    ("task", "s000_cqrs_cfs.cfs_proc_task_t"),
    ("route","s000_cqrs_cfs.cfs_proc_route_t"),
    ("msg",  "s000_cqrs_cfs.tpl_fd_message_t"),
]

# 35-column select list shared by approval/send/countersign inserts
_STATUS_VIEW_COLS = """oa.application_inst_id, CAST(oa.operator_application_id AS VARCHAR),
    oa.application_code, {period}, {period_dd}, {period_dd},
    oa.operator_application_id, '税票', '正项', '{node_type}', -999,
    oa.salesperson_id, oa.company_id, oa.customer_id, oa.contract_id,
    CAST(NULL AS BIGINT), {invoice_no},
    oa.operator_application_id, CAST(NULL AS VARCHAR),
    oa.currency_id, oa.total_amount, oa.creation_date,
    {submit_date}, oa.applicant_time,
    CAST(NULL AS BIGINT), {currentrole},
    CAST(NULL AS BIGINT), CAST(NULL AS BIGINT),
    CAST(NULL AS VARCHAR), CAST(NULL AS VARCHAR), CAST(NULL AS VARCHAR),
    oa.logical_is_deleted, oa.cdc_last_update_date, oa.logical_is_deleted_del,
    oa.tax_invoice_date, oa.payment_unit_number"""

_FACT_COLS = """id, head_id, application_code, period_id, period_id_dd, period_id_qty,
    business_id, bill_type, business_type, node_type, invoice_type_id,
    salesperson_id, company_id, customer_id, contract_id,
    invoice_id, invoice_no, operator_application_id, milestone_name,
    currency_id, total_amount, creation_date, submit_date, applicant_time,
    current_handler_id, currentrole, todo_billing_id, payment_unit_id,
    source_code, details_flag, billing_status, logical_is_deleted,
    cdc_last_update_date, tax_invoice_date, payment_unit_number"""


def build_maintain(dialect, q, tables, data_dir, slices_per_step,
                   step_start, insert_tag, del_start=None, del_tag=None,
                   load_deltas=True, ins_prefix="_ins_", del_prefix="_del_"):
    """Return the maintenance SQL for one step.
    dialect: 'duckdb' | 'opengauss'
    q: fn(table_name) -> qualified name for base tables and matviews
    tables: data_model.TABLES
    load_deltas=False: the runner has already staged the step's slices into
    {ins_prefix}<short>/{del_prefix}<short> tables (the MLog analog written as
    a byproduct of the base update); skip CSV loading and just apply deltas.
    """
    dd = dialect == "duckdb"

    def period(col):
        return (f"CAST(strftime({col}, '%Y%m') AS INTEGER)" if dd
                else f"CAST(to_char({col}, 'yyyyMM') AS INTEGER)")

    def period_dd(col):
        return (f"CAST(strftime({col}, '%Y%m%d') AS INTEGER)" if dd
                else f"CAST(to_char({col}, 'yyyyMMdd') AS INTEGER)")

    def bool_greatest(a, b):
        return (f"GREATEST(CAST({a} AS INTEGER), CAST({b} AS INTEGER))::BOOLEAN" if dd
                else f"greatest({a}, {b})")

    def mk_temp(name, body):
        if dd:
            return f"CREATE OR REPLACE TEMP TABLE {name} AS {body};"
        return f"DROP TABLE IF EXISTS {name}; CREATE TEMP TABLE {name} AS {body};"

    p = []
    w = p.append

    # ── Stage 0: delta temp tables (skipped when pre-staged by the runner) ──
    for short, fqn in (DELTA_TABLES if load_deltas else []):
        tdef = tables[fqn]
        ipaths = [data_dir / "dynamic" / insert_tag / f"pct_{step_start + i:03d}" / tdef.csv_name
                  for i in range(slices_per_step)]
        if dd:
            colspec = ", ".join(f"'{c.name}': '{c.dtype}'" for c in tdef.columns)
            union = "\nUNION ALL ".join(
                f"SELECT * FROM read_csv('{pp}', header=true, columns={{{colspec}}})" for pp in ipaths)
            w(f"CREATE OR REPLACE TEMP TABLE _ins_{short} AS {union};")
        else:
            cols_ddl = ", ".join(f"{c.name} {c.dtype}" for c in tdef.columns)
            w(f"DROP TABLE IF EXISTS _ins_{short}; CREATE TEMP TABLE _ins_{short} ({cols_ddl});")
            for pp in ipaths:
                w(f"COPY _ins_{short} FROM '{pp}' WITH (FORMAT csv, HEADER true, DELIMITER ',');")
        if del_start is not None:
            dpaths = [data_dir / "dynamic" / del_tag / f"pct_{del_start + i:03d}" / tdef.csv_name
                      for i in range(slices_per_step)]
            if dd:
                dunion = "\nUNION ALL ".join(
                    f"SELECT * FROM read_csv('{pp}', header=true, columns={{{colspec}}})" for pp in dpaths)
                w(f"CREATE OR REPLACE TEMP TABLE _del_{short} AS {dunion};")
            else:
                w(f"DROP TABLE IF EXISTS _del_{short}; CREATE TEMP TABLE _del_{short} ({cols_ddl});")
                for pp in dpaths:
                    w(f"COPY _del_{short} FROM '{pp}' WITH (FORMAT csv, HEADER true, DELIMITER ',');")
        else:
            if dd:
                w(f"CREATE OR REPLACE TEMP TABLE _del_{short} AS SELECT * FROM _ins_{short} LIMIT 0;")
            else:
                w(f"DROP TABLE IF EXISTS _del_{short}; CREATE TEMP TABLE _del_{short} ({cols_ddl});")

    # ── Stage 1: tmp_zx (pure delta transform; identity = (type, src_pk)) ──
    zx = q("tmp_zx_send_countersign_t_mv")
    w(mk_temp("_dz_del", f"""
SELECT application_code, approve_date, status, invoice_no, send_date,
       office_receive_date, customer_receive_date, tax_invoice_date, type, src_pk
FROM {zx}
WHERE (type = '1' AND src_pk IN (SELECT customer_invoice_id FROM _del_cinv))
   OR (type = '2' AND src_pk IN (SELECT invoice_id FROM _del_inv))"""))
    w(f"""DELETE FROM {zx}
WHERE (type = '1' AND src_pk IN (SELECT customer_invoice_id FROM _del_cinv))
   OR (type = '2' AND src_pk IN (SELECT invoice_id FROM _del_inv));""")
    w(mk_temp("_dz_ins", f"""
SELECT ccci.application_code, ccci.approve_date, ccci.status, ccci.invoice_no,
       ccci.send_date, ccci.office_receive_date, ccci.customer_receive_date,
       ccci.tax_invoice_date, '1' AS type, ccci.customer_invoice_id AS src_pk
FROM _ins_cinv ccci WHERE ccci.status >= 3
UNION ALL
SELECT cici.application_code, cici.approve_date, cici.status, cici.tax_invoice_no,
       cici.send_date, NULL, NULL, NULL, '2', cici.invoice_id
FROM _ins_inv cici WHERE cici.status IN (30, 40)"""))
    w(f"INSERT INTO {zx} SELECT * FROM _dz_ins;")

    # ── Stage 2: apt_mv (GROUP MAX with _ivm_count; job5 MERGE #3) ──
    apt = q("apt_mv")
    w(mk_temp("_da_ins", """
SELECT application_code AS c, MAX(tax_invoice_date) AS mx, COUNT(*) AS n
FROM _dz_ins WHERE type = '1' GROUP BY application_code"""))
    w(mk_temp("_da_del", """
SELECT application_code AS c, MAX(tax_invoice_date) AS mx, COUNT(*) AS n
FROM _dz_del WHERE type = '1' GROUP BY application_code"""))
    w(mk_temp("_apt_changed", "SELECT c FROM _da_ins UNION SELECT c FROM _da_del"))
    w(f"""UPDATE {apt} SET
    tax_invoice_date = CASE WHEN {apt}.tax_invoice_date IS NULL THEN d.mx
                            WHEN d.mx IS NULL THEN {apt}.tax_invoice_date
                            WHEN d.mx > {apt}.tax_invoice_date THEN d.mx
                            ELSE {apt}.tax_invoice_date END,
    _ivm_count = {apt}._ivm_count + d.n
FROM _da_ins d WHERE {apt}.application_code = d.c;""")
    w(f"""INSERT INTO {apt}
SELECT d.c, d.mx, d.n FROM _da_ins d
WHERE NOT EXISTS (SELECT 1 FROM {apt} t WHERE t.application_code = d.c);""")
    w(mk_temp("_apt_recalc", f"""
SELECT d.c FROM _da_del d JOIN {apt} a ON a.application_code = d.c
WHERE a._ivm_count > d.n
  AND (d.mx IS NOT NULL AND (a.tax_invoice_date IS NULL OR d.mx >= a.tax_invoice_date))"""))
    w(f"""UPDATE {apt} SET _ivm_count = {apt}._ivm_count - d.n
FROM _da_del d WHERE {apt}.application_code = d.c;""")
    w(mk_temp("_apt_removed", f"SELECT application_code FROM {apt} WHERE _ivm_count <= 0"))
    w(f"DELETE FROM {apt} WHERE _ivm_count <= 0;")
    w(f"""UPDATE {apt} SET tax_invoice_date = r.mx
FROM (SELECT application_code AS c, MAX(tax_invoice_date) AS mx
      FROM {zx} WHERE type = '1'
        AND application_code IN (SELECT c FROM _apt_recalc)
      GROUP BY application_code) r
WHERE {apt}.application_code = r.c;""")

    # ── Stage 3: tmp_cfs_opt (delta-join decomposition; job5 MERGE #4-#6) ──
    opt = q("tmp_cfs_opt_application_inst_t_mv")
    app_t = q("cfs_opt_application_t")
    inst_t = q("cfs_opt_application_inst_t")
    pu_t = q("cfs_con_payment_unit_t")
    opt_filter = ("oa.application_type = 1 AND oa.status IN (30, 40, 50) "
                  "AND oa.creation_date > TIMESTAMP '2022-01-01 00:00:00'")
    opt_select = f"""SELECT opii.application_inst_id, oa.operator_application_id, oa.application_code,
    oa.salesperson_id, oa.company_id, oa.customer_id, opii.contract_id,
    oa.currency_id, oa.total_amount, oa.creation_date, oa.applicant_time,
    oa.logical_is_deleted,
    GREATEST(oa.cdc_last_update_date, opii.cdc_last_update_date) AS cdc_last_update_date,
    oa.work_flow_id, oa.application_type, oa.status,
    {bool_greatest('oa.logical_is_deleted', 'opii.logical_is_deleted')} AS logical_is_deleted_del,
    opii.payment_unit_id, pu.payment_unit_number, apt.tax_invoice_date"""

    w(mk_temp("_do_del_ids", f"""
SELECT application_inst_id FROM _del_inst
UNION
SELECT application_inst_id FROM {opt}
WHERE operator_application_id IN (SELECT operator_application_id FROM _del_app)"""))
    w(f"DELETE FROM {opt} WHERE application_inst_id IN (SELECT application_inst_id FROM _do_del_ids);")
    w(mk_temp("_do_ins", f"""
{opt_select}
FROM _ins_inst opii
JOIN {app_t} oa ON oa.operator_application_id = opii.operator_application_id
LEFT JOIN {pu_t} pu ON opii.payment_unit_id = pu.payment_unit_id
LEFT JOIN {apt} apt ON oa.application_code = apt.application_code
WHERE {opt_filter}
UNION ALL
{opt_select}
FROM _ins_app oa
JOIN {inst_t} opii ON oa.operator_application_id = opii.operator_application_id
LEFT JOIN {pu_t} pu ON opii.payment_unit_id = pu.payment_unit_id
LEFT JOIN {apt} apt ON oa.application_code = apt.application_code
WHERE {opt_filter}
  AND opii.application_inst_id NOT IN (SELECT application_inst_id FROM _ins_inst)"""))
    w(f"INSERT INTO {opt} SELECT * FROM _do_ins;")
    # attribute deltas: Δpu, Δapt
    w(f"""UPDATE {opt} SET payment_unit_number = p.payment_unit_number
FROM _ins_pu p WHERE {opt}.payment_unit_id = p.payment_unit_id;""")
    w(f"""UPDATE {opt} SET payment_unit_number = NULL
WHERE payment_unit_id IN (SELECT payment_unit_id FROM _del_pu);""")
    w(f"""UPDATE {opt} SET tax_invoice_date = a.tax_invoice_date
FROM {apt} a WHERE {opt}.application_code = a.application_code
  AND a.application_code IN (SELECT c FROM _apt_changed);""")
    w(f"""UPDATE {opt} SET tax_invoice_date = NULL
WHERE application_code IN (SELECT application_code FROM _apt_removed);""")
    w(mk_temp("_d_opt_ids", f"""
SELECT application_inst_id FROM _do_del_ids
UNION SELECT application_inst_id FROM _do_ins
UNION SELECT application_inst_id FROM {opt}
WHERE payment_unit_id IN (SELECT payment_unit_id FROM _ins_pu
                          UNION SELECT payment_unit_id FROM _del_pu)
   OR application_code IN (SELECT c FROM _apt_changed)"""))

    # ── Stage 4: approval (job5 MERGE #8-#11: Δopt plus Δtask/Δroute) ──
    appr = q("approval_temp_mv")
    task_t, route_t, node_t = q("cfs_proc_task_t"), q("cfs_proc_route_t"), q("cfs_proc_node_define_t")
    w(mk_temp("_task_procs", f"""
SELECT proc_inst_id FROM _ins_task
UNION SELECT proc_inst_id FROM _del_task
UNION SELECT t.proc_inst_id FROM {task_t} t
WHERE t.route_id IN (SELECT route_id FROM _ins_route UNION SELECT route_id FROM _del_route)"""))
    w(mk_temp("_appr_ids", f"""
SELECT application_inst_id FROM _d_opt_ids
UNION SELECT application_inst_id FROM {opt}
WHERE status = 30 AND work_flow_id IN (SELECT proc_inst_id FROM _task_procs)"""))
    w(f"DELETE FROM {appr} WHERE id IN (SELECT application_inst_id FROM _appr_ids);")
    appr_cols = _STATUS_VIEW_COLS.format(
        period=period("oa.applicant_time"), period_dd=period_dd("oa.applicant_time"),
        node_type="待审批", invoice_no="CAST(NULL AS VARCHAR)",
        submit_date="oa.applicant_time", currentrole="node.node_define_name_cn")
    w(f"""INSERT INTO {appr}
SELECT {appr_cols}
FROM {opt} oa
LEFT JOIN {task_t} task ON oa.work_flow_id = task.proc_inst_id
LEFT JOIN {route_t} route ON task.route_id = route.route_id
LEFT JOIN {node_t} node ON route.node_define_id = node.node_define_id
WHERE oa.status = 30 AND oa.application_inst_id IN (SELECT application_inst_id FROM _appr_ids);""")

    # ── Stage 5: temp_mv (job5 MERGE #12; same machinery as apt) ──
    tmp = q("temp_mv")
    w(mk_temp("_dt30_ins", """
SELECT application_code AS c, MAX(approve_date) AS mx, COUNT(*) AS n
FROM _dz_ins WHERE status = 30 GROUP BY application_code"""))
    w(mk_temp("_dt30_del", """
SELECT application_code AS c, MAX(approve_date) AS mx, COUNT(*) AS n
FROM _dz_del WHERE status = 30 GROUP BY application_code"""))
    w(mk_temp("_temp_changed", "SELECT c FROM _dt30_ins UNION SELECT c FROM _dt30_del"))
    w(f"""UPDATE {tmp} SET
    approve_date = CASE WHEN {tmp}.approve_date IS NULL THEN d.mx
                        WHEN d.mx IS NULL THEN {tmp}.approve_date
                        WHEN d.mx > {tmp}.approve_date THEN d.mx
                        ELSE {tmp}.approve_date END,
    _ivm_count = {tmp}._ivm_count + d.n
FROM _dt30_ins d WHERE {tmp}.application_code = d.c;""")
    w(f"""INSERT INTO {tmp}
SELECT d.c, d.mx, d.n FROM _dt30_ins d
WHERE NOT EXISTS (SELECT 1 FROM {tmp} t WHERE t.application_code = d.c);""")
    w(mk_temp("_temp_recalc", f"""
SELECT d.c FROM _dt30_del d JOIN {tmp} a ON a.application_code = d.c
WHERE a._ivm_count > d.n
  AND (d.mx IS NOT NULL AND (a.approve_date IS NULL OR d.mx >= a.approve_date))"""))
    w(f"""UPDATE {tmp} SET _ivm_count = {tmp}._ivm_count - d.n
FROM _dt30_del d WHERE {tmp}.application_code = d.c;""")
    w(mk_temp("_temp_removed", f"SELECT application_code FROM {tmp} WHERE _ivm_count <= 0"))
    w(f"DELETE FROM {tmp} WHERE _ivm_count <= 0;")
    w(f"""UPDATE {tmp} SET approve_date = r.mx
FROM (SELECT application_code AS c, MAX(approve_date) AS mx
      FROM {zx} WHERE status = 30
        AND application_code IN (SELECT c FROM _temp_recalc)
      GROUP BY application_code) r
WHERE {tmp}.application_code = r.c;""")

    # ── Stage 6: send (job5 MERGE #13-#15: Δopt, Δtemp, Δmsg) ──
    send = q("send_temp_mv")
    msg_t = q("tpl_fd_message_t")
    w(mk_temp("_send_ids", f"""
SELECT application_inst_id FROM _d_opt_ids
UNION SELECT application_inst_id FROM {opt}
WHERE status = 40 AND application_code IN (SELECT c FROM _temp_changed
                                           UNION SELECT application_code FROM _temp_removed)
UNION SELECT application_inst_id FROM {opt}
WHERE status = 40 AND EXISTS (
    SELECT 1 FROM _ins_msg WHERE message_key = '{SPECIAL_MSG_KEY}'
    UNION ALL SELECT 1 FROM _del_msg WHERE message_key = '{SPECIAL_MSG_KEY}')"""))
    w(f"DELETE FROM {send} WHERE id IN (SELECT application_inst_id FROM _send_ids);")
    send_cols = _STATUS_VIEW_COLS.format(
        period=period("oa.applicant_time"), period_dd=period_dd("oa.applicant_time"),
        node_type="待寄送", invoice_no="CAST(NULL AS VARCHAR)",
        submit_date="temp.approve_date", currentrole="mes.message")
    w(f"""INSERT INTO {send}
SELECT {send_cols}
FROM {opt} oa
JOIN {tmp} temp ON temp.application_code = oa.application_code
LEFT JOIN {msg_t} mes ON mes.app_name = 'cfs' AND mes.language = 'zh_CN'
    AND mes.message_key = '{SPECIAL_MSG_KEY}'
WHERE oa.status = 40 AND oa.application_inst_id IN (SELECT application_inst_id FROM _send_ids);""")

    # ── Stage 7: tic (DISTINCT via reference counts; job5 MERGE #16) ──
    tic = q("tic_mv")
    tic_filter = "status >= 40 AND (office_receive_date IS NULL OR customer_receive_date IS NULL)"
    w(mk_temp("_dtic_ins", f"""
SELECT invoice_no, application_code, send_date, COUNT(*) AS n
FROM _dz_ins WHERE {tic_filter}
GROUP BY invoice_no, application_code, send_date"""))
    w(mk_temp("_dtic_del", f"""
SELECT invoice_no, application_code, send_date, COUNT(*) AS n
FROM _dz_del WHERE {tic_filter}
GROUP BY invoice_no, application_code, send_date"""))
    # application_code leads as a plain equality: it is never NULL (generator
    # guarantee; verified 0 NULLs at full scale in zx/tic/apt/temp), which
    # gives row engines a hashable/indexable join key — openGauss cannot hash
    # on IS NOT DISTINCT FROM and fell back to a nested loop costing 183 s per
    # step. The two genuinely nullable columns keep NULL-safe matching, so the
    # predicate is logically identical to the previous all-IS-NOT-DISTINCT form.
    nsafe = ("{t}.application_code = d.application_code "
             "AND {t}.invoice_no IS NOT DISTINCT FROM d.invoice_no "
             "AND {t}.send_date IS NOT DISTINCT FROM d.send_date")
    w(f"""UPDATE {tic} SET _ivm_count = {tic}._ivm_count + d.n
FROM _dtic_ins d WHERE {nsafe.format(t=tic)};""")
    w(f"""INSERT INTO {tic}
SELECT d.invoice_no, d.application_code, d.send_date, d.n
FROM _dtic_ins d
WHERE NOT EXISTS (SELECT 1 FROM {tic} t WHERE {nsafe.format(t='t')});""")
    w(f"""UPDATE {tic} SET _ivm_count = {tic}._ivm_count - d.n
FROM _dtic_del d WHERE {nsafe.format(t=tic)};""")
    w(f"DELETE FROM {tic} WHERE _ivm_count <= 0;")
    w(mk_temp("_tic_changed", """
SELECT application_code FROM _dtic_ins UNION SELECT application_code FROM _dtic_del"""))

    # ── Stage 8: countersign (job5 MERGE #17-#18: Δopt, Δtic) ──
    cs = q("countersign_temp_mv")
    w(mk_temp("_cs_ids", f"""
SELECT application_inst_id FROM _d_opt_ids
UNION SELECT application_inst_id FROM {opt}
WHERE status = 50 AND application_code IN (SELECT application_code FROM _tic_changed)"""))
    w(f"DELETE FROM {cs} WHERE id IN (SELECT application_inst_id FROM _cs_ids);")
    cs_cols = _STATUS_VIEW_COLS.format(
        period=period("oa.applicant_time"), period_dd=period_dd("oa.applicant_time"),
        node_type="待签返", invoice_no="tic.invoice_no",
        submit_date="tic.send_date", currentrole="'结束'")
    w(f"""INSERT INTO {cs}
SELECT {cs_cols}
FROM {opt} oa
JOIN {tic} tic ON tic.application_code = oa.application_code
WHERE oa.status = 50 AND oa.application_inst_id IN (SELECT application_inst_id FROM _cs_ids);""")

    # ── Stage 9: fact (job5 MERGE #19-#21: union of sub-view deltas) ──
    fact = q("fact_t_mv")
    w(mk_temp("_fact_ids", """
SELECT application_inst_id FROM _appr_ids
UNION SELECT application_inst_id FROM _send_ids
UNION SELECT application_inst_id FROM _cs_ids"""))
    w(f"DELETE FROM {fact} WHERE id IN (SELECT application_inst_id FROM _fact_ids);")
    for src in ["approval_temp_mv", "send_temp_mv", "countersign_temp_mv"]:
        w(f"""INSERT INTO {fact}
SELECT {_FACT_COLS}
FROM {q(src)} WHERE id IN (SELECT application_inst_id FROM _fact_ids);""")

    # ── cleanup ──
    temps = (([f"_ins_{s}" for s, _ in DELTA_TABLES] +
              [f"_del_{s}" for s, _ in DELTA_TABLES]) if load_deltas else []) + (
             ["_dz_del", "_dz_ins", "_da_ins", "_da_del", "_apt_changed", "_apt_recalc",
              "_apt_removed", "_do_del_ids", "_do_ins", "_d_opt_ids", "_task_procs",
              "_appr_ids", "_dt30_ins", "_dt30_del", "_temp_changed", "_temp_recalc",
              "_temp_removed", "_send_ids", "_dtic_ins", "_dtic_del", "_tic_changed",
              "_cs_ids", "_fact_ids"])
    for t in temps:
        w(f"DROP TABLE IF EXISTS {t};")

    sql = "\n".join(p)
    if ins_prefix != "_ins_" or del_prefix != "_del_":
        for short, _ in DELTA_TABLES:
            sql = sql.replace(f"_ins_{short}", f"{ins_prefix}{short}")
            sql = sql.replace(f"_del_{short}", f"{del_prefix}{short}")
    return sql
