#!/usr/bin/env python3
"""openGauss runner for the Job 5 streaming query-maintenance benchmark.

Same four methods, correctness checks, and metrics as run_duckdb.py, executed
against a running openGauss server via the `gsql` client. Each scenario runs in
its own schema (exp_ins / exp_sw / exp_prs).

  recompute      full recomputation query at each step
  logical_views  nine ordinary views, expanded by each query
  ivm            physical materialized tables (maintain/ivm_maintain.py)
  crown          CROWN semi-join/projection state (maintain/crown_maintain.py)

Session settings match a fair openGauss configuration: query_dop for
intra-query parallelism and enable_nestloop=off for the measured queries
(the tombstone anti-joins otherwise flip to pathological nested loops). The
ivm matview indexes and the crown state indexes are built at init and their
build time is recorded.

Requires: a running openGauss server and `gsql` on PATH (or set JOB5_GSQL to
the gsql wrapper). Connection is taken from gsql's own environment/.pgpass.
Data is NOT shipped; generate it first or point JOB5_DATA_DIR at it.

Usage:
  python3 run_opengauss.py [--scale 0.1] [--scenarios s1,s2] [--max-steps N]
                           [--out DIR]
"""

import argparse
import csv
import os
import subprocess
import sys
import time
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_DIR / "runner"))
sys.path.insert(0, str(PROJECT_DIR))
from data_model import TABLES, dynamic_tables, static_tables  # noqa: E402
from maintain import ivm_maintain, crown_maintain  # noqa: E402

GSQL_CMD = os.environ.get("JOB5_GSQL", "gsql")
QUERY_DOP = int(os.environ.get("QUERY_DOP", "32"))

# scale-dependent paths, set by configure()
SCALE = DATA_ROOT = DATA_DIR = STATIC_DIR = WORK_DIR = OUT_DIR = None
MAX_STEPS = None


def configure(scale, out=None, max_steps=None):
    """Set scale-dependent paths; call before the builders or run_scenario."""
    global SCALE, DATA_ROOT, DATA_DIR, STATIC_DIR, WORK_DIR, OUT_DIR, MAX_STEPS
    SCALE = str(scale)
    DATA_ROOT = Path(os.environ.get("JOB5_DATA_DIR", PROJECT_DIR / "data"))
    DATA_DIR = DATA_ROOT / f"scale_{SCALE}"
    STATIC_DIR = DATA_ROOT / "static"
    WORK_DIR = Path(os.environ.get("JOB5_SCRATCH", PROJECT_DIR / ".scratch"))
    OUT_DIR = Path(out) if out else PROJECT_DIR / "results" / "opengauss" / f"scale_{SCALE}"
    MAX_STEPS = max_steps


SLIDE_PERCENT = 5
WINDOW_PERCENT = 10
CSV_SLICE_PERCENT = 1
SLICES_PER_STEP = SLIDE_PERCENT // CSV_SLICE_PERCENT
TOTAL_STEPS = 100 // SLIDE_PERCENT

METHODS = ["recompute", "logical_views", "ivm", "crown"]
TARGET = {"recompute":     {"dtl": "dtl_rc", "sum": "sum_rc"},
          "logical_views": {"dtl": "dtl_lv", "sum": "sum_lv"},
          "ivm":           {"dtl": "dtl_mv", "sum": "sum_mv"},
          "crown":         {"dtl": "dtl_cw", "sum": "sum_cw"}}
_SCHEMA_PREFIX = os.environ.get("JOB5_SCHEMA_PREFIX", "exp")
SCHEMA_MAP = {"insertion_only": f"{_SCHEMA_PREFIX}_ins",
              "sliding_window": f"{_SCHEMA_PREFIX}_sw",
              "preloaded_replacement_sliding": f"{_SCHEMA_PREFIX}_prs"}
MV_NAMES = crown_maintain.MV_NAMES
CROWN_TABLES = crown_maintain.CROWN_TABLES
VOLATILE_COLS = crown_maintain.VOLATILE_COLS
UNORDERED_AGG_COLS = crown_maintain.UNORDERED_AGG_COLS

STAGE_SHORT = {
    "s000_cqrs_cfs.cfs_cinv_customer_invoice_t": "cinv",
    "s000_cqrs_cfs.cfs_inv_invoice_info_t": "inv",
    "s000_cqrs_cfs.cfs_opt_application_t": "app",
    "s000_cqrs_cfs.cfs_opt_application_inst_t": "inst",
    "s000_cqrs_cfs.cfs_con_payment_unit_t": "pu",
    "s000_cqrs_cfs.cfs_proc_task_t": "task",
    "s000_cqrs_cfs.cfs_proc_route_t": "route",
    "s000_cqrs_cfs.tpl_fd_message_t": "msg",
    "s000_cqrs_cfs.cfs_cfg_company_t": "company",
    "s000_dwt_hws_iao.cfs_comm_contract_t": "contract",
    "s000_cqrs_cfs.tpl_user_t": "user",
}

# ivm matview indexes (physical-ctid identity replaced by the stable source
# keys the maintenance logic probes; build time reported at init)
MV_INDEX_DDL = [
    "CREATE INDEX zx_mv_srcpk ON {s}.tmp_zx_send_countersign_t_mv (type, src_pk)",
    "CREATE INDEX zx_mv_code ON {s}.tmp_zx_send_countersign_t_mv (application_code)",
    "CREATE INDEX apt_mv_code ON {s}.apt_mv (application_code)",
    "CREATE INDEX opt_mv_inst ON {s}.tmp_cfs_opt_application_inst_t_mv (application_inst_id)",
    "CREATE INDEX opt_mv_app ON {s}.tmp_cfs_opt_application_inst_t_mv (operator_application_id)",
    "CREATE INDEX opt_mv_pu ON {s}.tmp_cfs_opt_application_inst_t_mv (payment_unit_id)",
    "CREATE INDEX opt_mv_code ON {s}.tmp_cfs_opt_application_inst_t_mv (application_code)",
    "CREATE INDEX appr_mv_id ON {s}.approval_temp_mv (id)",
    "CREATE INDEX temp_mv_code ON {s}.temp_mv (application_code)",
    "CREATE INDEX send_mv_id ON {s}.send_temp_mv (id)",
    "CREATE INDEX tic_mv_code ON {s}.tic_mv (application_code)",
    "CREATE INDEX cs_mv_id ON {s}.countersign_temp_mv (id)",
    "CREATE INDEX fact_mv_id ON {s}.fact_t_mv (id)",
]


# ── gsql helpers ──

def gsql(sql_text, label=""):
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    tmp = WORK_DIR / f"_og_{os.getpid()}.sql"
    tmp.write_text(sql_text, encoding="utf-8")
    r = subprocess.run([GSQL_CMD, "-t", "-A", "-f", str(tmp)],
                       capture_output=True, text=True, timeout=14400)
    combined = r.stdout + r.stderr
    fatal = ["syntax error", "permission denied", "could not open file",
             "out of memory", "connection refused", "does not exist"]
    errs = [l for l in combined.splitlines() if "ERROR:" in l and any(k in l.lower() for k in fatal)]
    if errs:
        raise RuntimeError(f"gsql error [{label}]: {combined[:2000]}")
    return "\n".join(l for l in r.stdout.splitlines()
                     if l.strip() not in ("SET", "") and not l.strip().startswith("total time:"))


def gsql_timed(sql_text, label=""):
    t0 = time.perf_counter()
    out = gsql(sql_text, label)
    return (time.perf_counter() - t0) * 1000, out


def gsql_fetch(sql_text, label=""):
    ms, out = gsql_timed(sql_text, label)
    rows = [tuple(l.split("|")) for l in out.strip().splitlines() if l.strip()]
    return ms, rows


def sp(schema):
    return f"SET search_path = {schema}, public;\nSET query_dop = {QUERY_DOP};\n"


def qsp(schema):
    return sp(schema) + "SET enable_nestloop = off;\n"


def read_sql(path):
    return (PROJECT_DIR / path).read_text(encoding="utf-8")


def rebind(sql, schema):
    sql = sql.replace("s000_cqrs_cfs.", f"{schema}.").replace("s000_dwt_hws_iao.", f"{schema}.")
    sql = sql.replace("SET search_path = s000_cqrs_cfs, s000_dwt_hws_iao, public;",
                      f"SET search_path = {schema}, public;")
    return sql.replace(f"SET search_path = {schema}., {schema}., public;",
                       f"SET search_path = {schema}, public;")


def analyze_sql(schema, tables):
    return sp(schema) + "\n".join(f"ANALYZE {schema}.{t};" for t in tables)


# ── SQL builders ──

def build_init_sql(schema, scenario):
    parts = [f"CREATE SCHEMA IF NOT EXISTS {schema};", sp(schema)]
    base = rebind(read_sql("sql/opengauss/init/00_create_schema_and_tables.sql"), schema)
    base = base.replace("CREATE SCHEMA IF NOT EXISTS", "-- skip: CREATE SCHEMA IF NOT EXISTS")
    parts.append(base)
    parts.append(rebind(read_sql("sql/opengauss/init/01_create_primary_keys_and_indexes.sql"), schema))
    dtl_tdef = TABLES["s000_dwt_hws_iao.dwd_billing_In_transit_dtl_t_05"]
    sum_tdef = TABLES["s000_dwt_hws_iao.dwd_billing_In_transit_t_05"]
    for method, aliases in TARGET.items():
        dtl_cols = ", ".join(f"{c.name} {c.dtype}" for c in dtl_tdef.columns)
        sum_cols = ", ".join(f"{c.name} {c.dtype}" for c in sum_tdef.columns)
        parts.append(f"CREATE TABLE {schema}.{aliases['dtl']} ({dtl_cols});")
        parts.append(f"CREATE TABLE {schema}.{aliases['sum']} ({sum_cols});")
        parts.append(f"CREATE INDEX {aliases['dtl']}_pk ON {schema}.{aliases['dtl']} (id, logical_is_deleted);")
        parts.append(f"CREATE INDEX {aliases['sum']}_pk ON {schema}.{aliases['sum']} (head_id, logical_is_deleted);")
    for fqn, tdef in sorted(static_tables().items()):
        parts.append(f"COPY {schema}.{tdef.table} FROM '{STATIC_DIR / tdef.csv_name}'"
                     f" WITH (FORMAT csv, HEADER true, DELIMITER ',');")
    if scenario == "preloaded_replacement_sliding":
        for fqn, tdef in sorted(dynamic_tables().items()):
            for pct in range(1, 101):
                p = DATA_DIR / "dynamic" / "base" / f"pct_{pct:03d}" / tdef.csv_name
                parts.append(f"COPY {schema}.{tdef.table} FROM '{p}' WITH (FORMAT csv, HEADER true, DELIMITER ',');")
    for fqn, tdef in sorted(dynamic_tables().items()):
        short = STAGE_SHORT[fqn]
        cols = ", ".join(f"{c.name} {c.dtype}" for c in tdef.columns)
        parts.append(f"CREATE TABLE {schema}.mlog_ins_{short} ({cols});")
        parts.append(f"CREATE TABLE {schema}.mlog_del_{short} ({cols});")
    parts.append(analyze_sql(schema, [t.table for _, t in sorted(static_tables().items())]))
    if scenario == "preloaded_replacement_sliding":
        parts.append(analyze_sql(schema, [t.table for _, t in sorted(dynamic_tables().items())]))
    return "\n".join(parts)


def build_lv_init_sql(schema):
    lv = rebind(read_sql("sql/opengauss/logical_views/init.sql"), schema)
    for v in MV_NAMES:
        lv = lv.replace(v, v.replace("_mv", "_lv"))
    return sp(schema) + lv


def build_ivm_init_sql(schema):
    return sp(schema) + rebind(read_sql("sql/opengauss/ivm/init.sql"), schema)


def build_mv_index_sql(schema):
    return sp(schema) + ";\n".join(d.format(s=schema) for d in MV_INDEX_DDL) + ";"


def build_staging_sql(schema, step_start, insert_tag, del_start=None, del_tag=None):
    parts = [sp(schema)]
    for fqn, tdef in sorted(dynamic_tables().items()):
        short = STAGE_SHORT[fqn]
        parts.append(f"TRUNCATE {schema}.mlog_ins_{short};")
        parts.append(f"TRUNCATE {schema}.mlog_del_{short};")
        for i in range(SLICES_PER_STEP):
            p = DATA_DIR / "dynamic" / insert_tag / f"pct_{step_start + i:03d}" / tdef.csv_name
            parts.append(f"COPY {schema}.mlog_ins_{short} FROM '{p}' WITH (FORMAT csv, HEADER true, DELIMITER ',');")
        if del_start is not None:
            for i in range(SLICES_PER_STEP):
                p = DATA_DIR / "dynamic" / del_tag / f"pct_{del_start + i:03d}" / tdef.csv_name
                parts.append(f"COPY {schema}.mlog_del_{short} FROM '{p}' WITH (FORMAT csv, HEADER true, DELIMITER ',');")
    return "\n".join(parts)


def build_insert_sql(schema):
    return sp(schema) + "\n".join(
        f"INSERT INTO {schema}.{tdef.table} SELECT * FROM {schema}.mlog_ins_{STAGE_SHORT[fqn]};"
        for fqn, tdef in sorted(dynamic_tables().items()))


def build_delete_sql(schema):
    parts = [sp(schema)]
    for fqn, tdef in sorted(dynamic_tables().items()):
        cond = " AND ".join(f"t.{pk} = dk.{pk}" for pk in tdef.pk_columns)
        parts.append(f"DELETE FROM {schema}.{tdef.table} t USING {schema}.mlog_del_{STAGE_SHORT[fqn]} dk WHERE {cond};")
    return "\n".join(parts)


def _fixup_insert(sql, schema, qname, dtl_table, sum_table):
    target = dtl_table if qname in ("q1", "q2") else sum_table
    pk_col = "id" if qname in ("q1", "q2") else "head_id"
    sql = sql.replace("SELECT COUNT(*) AS cnt FROM (", "SELECT * FROM (")
    sql = sql.replace(") AS q;",
        f") AS _new WHERE NOT EXISTS (SELECT 1 FROM {schema}.{target} _t"
        f" WHERE _t.{pk_col} = CAST(_new.{pk_col} AS VARCHAR)"
        f" AND _t.logical_is_deleted = _new.logical_is_deleted);")
    sql = sql.replace(f"{schema}.dwd_billing_in_transit_dtl_t_05", f"{schema}.{dtl_table}")
    sql = sql.replace(f"{schema}.dwd_billing_in_transit_t_05", f"{schema}.{sum_table}")
    return f"INSERT INTO {schema}.{target}\n{sql}"


def build_recompute_insert(schema, qname, dtl, sm):
    sql = rebind(read_sql(f"sql/opengauss/recompute/{qname}_count.sql"), schema)
    return qsp(schema) + _fixup_insert(sql, schema, qname, dtl, sm)


def build_view_insert(schema, qname, dtl, sm, suffix):
    """query file with the nine view names rebound to a method suffix."""
    sql = rebind(read_sql(f"sql/opengauss/query/{qname}_count.sql"), schema)
    for v in MV_NAMES:
        sql = sql.replace(v, v.replace("_mv", suffix))
    if suffix == "_cw" and qname == "q3":
        sql = crown_maintain.crown_q3_rebind(sql)  # scope reads crown_fact_ids
    return qsp(schema) + _fixup_insert(sql, schema, qname, dtl, sm)


def build_ivm_insert(schema, qname, dtl, sm):
    sql = rebind(read_sql(f"sql/opengauss/query/{qname}_count.sql"), schema)
    return qsp(schema) + _fixup_insert(sql, schema, qname, dtl, sm)


def build_query(schema, method, qname, dtl, sm):
    if method == "recompute":
        return build_recompute_insert(schema, qname, dtl, sm)
    if method == "logical_views":
        return build_view_insert(schema, qname, dtl, sm, "_lv")
    if method == "ivm":
        return build_ivm_insert(schema, qname, dtl, sm)
    return build_view_insert(schema, qname, dtl, sm, "_cw")


def build_ivm_maintain(schema, step_start, insert_tag, del_start=None, del_tag=None):
    q = lambda name: name  # bare names; search_path set by sp(schema)
    body = ivm_maintain.build_maintain("opengauss", q, TABLES, DATA_DIR, SLICES_PER_STEP,
                                       step_start, insert_tag, del_start, del_tag,
                                       load_deltas=False,
                                       ins_prefix="mlog_ins_", del_prefix="mlog_del_")
    return sp(schema) + body


def count_form_sql(schema, method, qname, dtl, sm):
    """Count FORM of query qname. crown computes q1/q2/q3 by aggregating partial
    counts (no full join); others count their view/table result directly."""
    if method == "crown" and qname in ("q1", "q2"):
        return qsp(schema) + crown_maintain.crown_count_sql("opengauss", qname, dtl)
    if method == "recompute":
        sql = read_sql(f"sql/opengauss/recompute/{qname}_count.sql")
    else:
        sql = read_sql(f"sql/opengauss/query/{qname}_count.sql")
        suffix = {"logical_views": "_lv", "ivm": "_mv", "crown": "_cw"}[method]
        if suffix != "_mv":
            for v in MV_NAMES:
                sql = sql.replace(v, v.replace("_mv", suffix))
        if method == "crown" and qname == "q3":
            sql = crown_maintain.crown_q3_rebind(sql)  # scope reads crown_fact_ids
    sql = rebind(sql, schema)
    sql = sql.replace(f"{schema}.dwd_billing_in_transit_dtl_t_05", f"{schema}.{dtl}")
    sql = sql.replace(f"{schema}.dwd_billing_in_transit_t_05", f"{schema}.{sm}")
    return qsp(schema) + sql


def build_count_query(schema, table):
    return sp(schema) + f"SELECT COUNT(*) FROM {schema}.{table};"


def build_minmax_query(schema, table, is_dtl):
    if is_dtl:
        return sp(schema) + (f"SELECT MIN(id), MAX(id), MIN(application_code), MAX(application_code),"
                             f" MIN(submit_date), MAX(submit_date), MIN(total_amount), MAX(total_amount)"
                             f" FROM {schema}.{table};")
    return sp(schema) + (f"SELECT MIN(head_id), MAX(head_id), MIN(total_amount), MAX(total_amount)"
                         f" FROM {schema}.{table};")


# ── checks ──

RESULT_KINDS = (("dtl", "s000_dwt_hws_iao.dwd_billing_In_transit_dtl_t_05", VOLATILE_COLS),
                ("sum", "s000_dwt_hws_iao.dwd_billing_In_transit_t_05",
                 VOLATILE_COLS | UNORDERED_AGG_COLS))


def multiset_diff(schema, a, b, label):
    _, rows = gsql_fetch(sp(schema) +
        f"SELECT count(*) FROM (({a} EXCEPT ALL {b}) UNION ALL ({b} EXCEPT ALL {a})) x;", label)
    return int(rows[0][0])


def deep_compare(schema, scenario, checks):
    for kind, tkey, excl in RESULT_KINDS:
        cols = [c.name for c in TABLES[tkey].columns if c.name not in excl]
        det = ", ".join(cols)
        for m1, m2 in (("recompute", "logical_views"), ("recompute", "ivm"), ("recompute", "crown")):
            n = multiset_diff(schema, f"SELECT {det} FROM {schema}.{TARGET[m1][kind]}",
                              f"SELECT {det} FROM {schema}.{TARGET[m2][kind]}", f"cmp/{kind}/{m1}_{m2}")
            checks.append(dict(scenario=scenario, check=f"final_{kind}_{m1}_vs_{m2}", mismatches=n))
    n = multiset_diff(schema, f"SELECT * FROM {schema}.fact_t_mv",
                      f"SELECT * FROM {schema}.fact_t_cw", "cmp/fact")
    checks.append(dict(scenario=scenario, check="final_fact_ivm_vs_crown", mismatches=n))


# ── runner ──

def plan_steps(scenario):
    """Per-step update plan (slice ranges, insert/delete tags) for a scenario."""
    plan = []
    for step_idx in range(TOTAL_STEPS):
        step_start = step_idx * SLICES_PER_STEP + 1
        step_pct = (step_idx + 1) * SLIDE_PERCENT
        insert_tag = "extra" if scenario == "preloaded_replacement_sliding" else "base"
        do_delete, del_start, del_tag = False, None, None
        if scenario == "sliding_window":
            boundary = step_pct - WINDOW_PERCENT
            if boundary > 0:
                do_delete = True
                del_start = (boundary - SLIDE_PERCENT) // CSV_SLICE_PERCENT + 1
                del_tag = "base"
        elif scenario == "preloaded_replacement_sliding":
            do_delete, del_start, del_tag = True, step_start, "base"
        plan.append(dict(step_idx=step_idx, step_start=step_start, step_pct=step_pct,
                         insert_tag=insert_tag, do_delete=do_delete,
                         del_start=del_start, del_tag=del_tag))
    return plan


def run_scenario(scenario):
    schema = SCHEMA_MAP[scenario]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    metrics, checks = [], []
    log = open(OUT_DIR / f"{scenario}.log", "w", encoding="utf-8")

    def say(msg):
        print(f"  [{scenario}] {msg}", flush=True)
        log.write(msg + "\n"); log.flush()

    def emit(step, phase, method, qname, ms):
        metrics.append(dict(scenario=scenario, step=step, phase=phase, method=method,
                            qname=qname, seconds=round(ms / 1000, 4)))

    gsql(f"DROP SCHEMA IF EXISTS {schema} CASCADE;", "drop")
    ms, _ = gsql_timed(build_init_sql(schema, scenario), "init"); emit(0, "init_base", "", "", ms)

    ms, _ = gsql_timed(build_lv_init_sql(schema), "lv/init"); emit(0, "init_method", "logical_views", "", ms)
    ms, _ = gsql_timed(build_ivm_init_sql(schema), "ivm/init"); emit(0, "init_method", "ivm", "", ms)
    ix, _ = gsql_timed(build_mv_index_sql(schema), "ivm/indexes"); emit(0, "init_index", "ivm", "", ix)
    ms, _ = gsql_timed(sp(schema) + crown_maintain.opengauss_state_init_sql(), "crown/init")
    emit(0, "init_method", "crown", "", ms)
    ix, _ = gsql_timed(sp(schema) + crown_maintain.opengauss_index_sql(schema), "crown/indexes")
    emit(0, "init_index", "crown", "", ix)
    lv_text = read_sql("sql/opengauss/logical_views/init.sql")
    gsql(sp(schema) + crown_maintain.opengauss_assembly_views_sql(lv_text, schema), "crown/views")
    ms, _ = gsql_timed(sp(schema) + crown_maintain.fact_ids_init_sql(), "crown/fact_ids")
    emit(0, "init_index", "crown", "", ms)
    say("init done")

    if scenario == "preloaded_replacement_sliding":
        ms, _ = gsql_timed(analyze_sql(schema, MV_NAMES + CROWN_TABLES), "analyze/init")
        emit(0, "analyze", "", "", ms)

    plan = plan_steps(scenario)
    if MAX_STEPS is not None:
        plan = plan[:MAX_STEPS]
    mismatch_total = 0
    mlog_del_analyzed = False

    for pstep in plan:
        step_idx = pstep["step_idx"]
        step_start = pstep["step_start"]
        step_pct = pstep["step_pct"]
        insert_tag = pstep["insert_tag"]
        do_delete = pstep["do_delete"]
        del_start = pstep["del_start"]
        del_tag = pstep["del_tag"]

        ms, _ = gsql_timed(build_staging_sql(schema, step_start, insert_tag,
                                             del_start if do_delete else None,
                                             del_tag if do_delete else None), "staging")
        emit(step_pct, "staging", "", "", ms)
        ms, _ = gsql_timed(build_insert_sql(schema), "base_insert"); emit(step_pct, "base_insert", "", "", ms)
        if do_delete:
            ms, _ = gsql_timed(build_delete_sql(schema), "base_delete"); emit(step_pct, "base_delete", "", "", ms)

        # first-batch statistics
        an = []
        if step_idx == 0 and scenario != "preloaded_replacement_sliding":
            an += [t.table for _, t in sorted(dynamic_tables().items())]
        if step_idx == 0:
            an += [f"mlog_ins_{STAGE_SHORT[f]}" for f in sorted(dynamic_tables())]
        if do_delete and not mlog_del_analyzed:
            an += [f"mlog_del_{STAGE_SHORT[f]}" for f in sorted(dynamic_tables())]
            mlog_del_analyzed = True
        if an:
            ms, _ = gsql_timed(analyze_sql(schema, an), "analyze/first"); emit(step_pct, "analyze", "", "", ms)

        step_res = {}
        cf_res = {}
        for method in METHODS:
            dtl, sm = TARGET[method]["dtl"], TARGET[method]["sum"]
            if method == "ivm":
                ms, _ = gsql_timed(build_ivm_maintain(schema, step_start, insert_tag,
                                                      del_start if do_delete else None,
                                                      del_tag if do_delete else None), "ivm/maintain")
                emit(step_pct, "maintain", "ivm", "", ms)
                if step_idx == 0 and scenario != "preloaded_replacement_sliding":
                    ms, _ = gsql_timed(analyze_sql(schema, MV_NAMES), "analyze/mv"); emit(step_pct, "analyze", "ivm", "", ms)
            elif method == "crown":
                ms, _ = gsql_timed(sp(schema) + crown_maintain.opengauss_maintain_sql()
                                   + "\n" + crown_maintain.fact_ids_maintain_sql("opengauss"), "crown/maintain")
                emit(step_pct, "maintain", "crown", "", ms)
                if step_idx == 0 and scenario != "preloaded_replacement_sliding":
                    ms, _ = gsql_timed(analyze_sql(schema, CROWN_TABLES), "analyze/crown"); emit(step_pct, "analyze", "crown", "", ms)
            for qname in ["q1", "q2", "q3", "q4"]:
                # accumulate INSERT: build the output tables (feeds q2/q3/q4)
                ms, _ = gsql_timed(build_query(schema, method, qname, dtl, sm), f"{method}/{qname}")
                emit(step_pct, "query", method, qname, ms)
                tbl = dtl if qname in ("q1", "q2") else sm
                _, cr = gsql_fetch(build_count_query(schema, tbl), f"{method}/{qname}/c")
                _, mr = gsql_fetch(build_minmax_query(schema, tbl, qname in ("q1", "q2")), f"{method}/{qname}/m")
                step_res[(method, qname)] = (cr[0][0] if cr else "", mr[0] if mr else ())
                # count form: crown aggregates partial counts (no full join);
                # others count their view/table result directly
                cms, cfr = gsql_fetch(count_form_sql(schema, method, qname, dtl, sm), f"{method}/{qname}/cf")
                emit(step_pct, "count_query", method, qname, cms)
                cf_res[(method, qname)] = cfr[0][0] if cfr else ""

        if step_idx == 0:
            tgt = [a["dtl"] for a in TARGET.values()] + [a["sum"] for a in TARGET.values()]
            ms, _ = gsql_timed(analyze_sql(schema, tgt), "analyze/targets"); emit(step_pct, "analyze", "", "", ms)

        step_ok = True
        for qname in ["q1", "q2", "q3", "q4"]:
            cref = cf_res[("recompute", qname)]
            for m in ("logical_views", "ivm", "crown"):
                if cf_res[(m, qname)] != cref:
                    step_ok = False
                    mismatch_total += 1
                    checks.append(dict(scenario=scenario,
                                       check=f"step{step_pct}_{qname}_countform_recompute_vs_{m}",
                                       mismatches=1, detail=f"{cref} != {cf_res[(m, qname)]}"))
            ref = step_res[("recompute", qname)]
            for m in ("logical_views", "ivm", "crown"):
                if step_res[(m, qname)] != ref:
                    step_ok = False
                    mismatch_total += 1
                    checks.append(dict(scenario=scenario, check=f"step{step_pct}_{qname}_recompute_vs_{m}",
                                       mismatches=1, detail=f"{ref} != {step_res[(m, qname)]}"))
        counts = " ".join(f"{q}={step_res[('recompute', q)][0]}" for q in ["q1", "q2", "q3", "q4"])
        say(f"step {step_pct:>3}%  {'ok ' if step_ok else 'MISMATCH'} {counts}")

    deep_compare(schema, scenario, checks)
    final = [c for c in checks if c["check"].startswith("final_")]
    say("final multiset comparisons: " +
        ", ".join(f"{c['check'].replace('final_', '')}={c['mismatches']}" for c in final))
    log.close()
    return metrics, checks, mismatch_total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scale", default="0.1")
    ap.add_argument("--scenarios", default="insertion_only,sliding_window,preloaded_replacement_sliding")
    ap.add_argument("--max-steps", type=int, default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    configure(args.scale, args.out, args.max_steps)

    if not DATA_DIR.exists():
        sys.exit(f"data dir not found: {DATA_DIR}\n"
                 f"generate data first (see README) or set JOB5_DATA_DIR.")
    all_metrics, all_checks, bad = [], [], 0
    scenarios = [s.strip() for s in args.scenarios.split(",") if s.strip()]
    print(f"=== openGauss: scale={SCALE}, scenarios={scenarios} ===", flush=True)
    print(f"    data: {DATA_DIR}\n    gsql: {GSQL_CMD}\n    out:  {OUT_DIR}", flush=True)
    for sc in scenarios:
        t0 = time.perf_counter()
        m, c, mm = run_scenario(sc)
        all_metrics += m; all_checks += c
        bad += mm + sum(x["mismatches"] for x in c if x["check"].startswith("final_"))
        print(f"  [{sc}] done in {time.perf_counter() - t0:.1f}s", flush=True)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_DIR / "metrics.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["scenario", "step", "phase", "method", "qname", "seconds"])
        w.writeheader(); w.writerows(all_metrics)
    with open(OUT_DIR / "checks.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["scenario", "check", "mismatches", "detail"])
        w.writeheader()
        for c in all_checks:
            c.setdefault("detail", ""); w.writerow(c)

    print(f"\n=== {'ALL RESULTS IDENTICAL' if bad == 0 else f'{bad} MISMATCHES'} ===")
    sys.exit(0 if bad == 0 else 1)


if __name__ == "__main__":
    main()
