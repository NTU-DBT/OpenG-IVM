#!/usr/bin/env python3
"""DuckDB runner for the Job 5 streaming query-maintenance benchmark.

Runs all four maintenance methods per step against one in-process DuckDB
database per scenario, records per-phase timings, and checks that every method
produces identical query results:

  recompute      full CTE recomputation at each step (no persistent state)
  logical_views  nine ordinary views, expanded by each query at run time
  ivm            physical materialized tables maintained by the translated
                 job5_ivm.sql delta logic (maintain/ivm_maintain.py)
  crown          CROWN-style semi-join/projection state maintained by change
                 propagation (maintain/crown_maintain.py); queries assemble
                 the result by joining the partial results in one SQL query

Per step the four benchmark queries q1-q4 are run in count-accumulation form
(INSERT ... WHERE NOT EXISTS) into per-method target tables; counts and
min/max are compared across methods every step, and the accumulated
detail/summary tables plus fact_t are compared as multisets at scenario end.

The SQL-building functions here are also reused by gen_sql.py to emit
standalone per-method SQL scripts. Call configure(scale) before using them.

Data is NOT shipped with this project. Generate it first (see README), or
point JOB5_DATA_DIR at an existing data directory.

Usage:
  python3 run_duckdb.py [--scale 0.1] [--scenarios s1,s2] [--max-steps N]
                        [--out DIR]
"""

import argparse
import csv
import os
import sys
import time
from pathlib import Path

import duckdb

PROJECT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_DIR / "runner"))
sys.path.insert(0, str(PROJECT_DIR))
from data_model import TABLES, dynamic_tables, static_tables  # noqa: E402
from maintain import ivm_maintain, crown_maintain  # noqa: E402

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
MV_NAMES = crown_maintain.MV_NAMES
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

# scale-dependent paths, set by configure()
SCALE = DATA_ROOT = DATA_DIR = STATIC_DIR = SCRATCH = OUT_DIR = None
MAX_STEPS = None


def configure(scale, out=None, max_steps=None):
    """Set scale-dependent paths; call before the builders or run_scenario."""
    global SCALE, DATA_ROOT, DATA_DIR, STATIC_DIR, SCRATCH, OUT_DIR, MAX_STEPS
    SCALE = str(scale)
    DATA_ROOT = Path(os.environ.get("JOB5_DATA_DIR", PROJECT_DIR / "data"))
    DATA_DIR = DATA_ROOT / f"scale_{SCALE}"
    STATIC_DIR = DATA_ROOT / "static"
    SCRATCH = Path(os.environ.get("JOB5_SCRATCH", PROJECT_DIR / ".scratch"))
    OUT_DIR = Path(out) if out else PROJECT_DIR / "results" / "duckdb" / f"scale_{SCALE}"
    MAX_STEPS = max_steps


# ── SQL builders ──

def read_sql(path):
    return (PROJECT_DIR / path).read_text(encoding="utf-8")


def strip_comments(sql):
    return "\n".join(l for l in sql.splitlines() if not l.strip().startswith("--"))


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


def init_base_sql(scenario):
    """Schema, base tables, per-method target tables, static data, preload."""
    parts = ["CREATE SCHEMA IF NOT EXISTS s000_cqrs_cfs;",
             "CREATE SCHEMA IF NOT EXISTS s000_dwt_hws_iao;",
             strip_comments(read_sql("sql/duckdb/init/00_create_schema_and_tables.sql")),
             strip_comments(read_sql("sql/duckdb/init/01_create_primary_keys_and_indexes.sql"))]
    for kind, fqn in (("dtl", "s000_dwt_hws_iao.dwd_billing_In_transit_dtl_t_05"),
                      ("sum", "s000_dwt_hws_iao.dwd_billing_In_transit_t_05")):
        cols = ", ".join(f"{c.name} {c.dtype}" for c in TABLES[fqn].columns)
        for m in METHODS:
            parts.append(f"CREATE TABLE {TARGET[m][kind]} ({cols});")
    for fqn, tdef in sorted(static_tables().items()):
        parts.append(f"COPY {tdef.fqn} FROM '{STATIC_DIR / tdef.csv_name}' (HEADER true, DELIMITER ',');")
    if scenario == "preloaded_replacement_sliding":
        for fqn, tdef in sorted(dynamic_tables().items()):
            for pct in range(1, 101):
                p = DATA_DIR / "dynamic" / "base" / f"pct_{pct:03d}" / tdef.csv_name
                parts.append(f"COPY {tdef.fqn} FROM '{p}' (HEADER true, DELIMITER ',');")
    return "\n".join(parts)


def init_method_sql(method):
    """Persistent objects a method needs (empty for recompute)."""
    if method == "logical_views":
        lv = strip_comments(read_sql("sql/duckdb/logical_views/init.sql"))
        for v in MV_NAMES:
            lv = lv.replace(v, v.replace("_mv", "_lv"))
        return lv
    if method == "ivm":
        return strip_comments(read_sql("sql/duckdb/ivm/init.sql"))
    if method == "crown":
        lv_text = strip_comments(read_sql("sql/duckdb/logical_views/init.sql"))
        return (crown_maintain.duckdb_state_init_sql()
                + crown_maintain.duckdb_assembly_views_sql(lv_text))
    return ""


def staging_sql(step_start, insert_tag, do_delete, del_start, del_tag):
    parts = []
    for fqn, tdef in sorted(dynamic_tables().items()):
        short = STAGE_SHORT[fqn]
        colspec = ", ".join(f"'{c.name}': '{c.dtype}'" for c in tdef.columns)
        # read_csv accepts a file list, so the column spec appears once per
        # table per step instead of once per slice (keeps the emitted SQL small)
        ins_list = "[" + ", ".join(
            f"'{DATA_DIR / 'dynamic' / insert_tag / f'pct_{step_start + i:03d}' / tdef.csv_name}'"
            for i in range(SLICES_PER_STEP)) + "]"
        parts.append(f"CREATE OR REPLACE TEMP TABLE _ins_{short} AS "
                     f"SELECT * FROM read_csv({ins_list}, header=true, columns={{{colspec}}});")
        if do_delete:
            del_list = "[" + ", ".join(
                f"'{DATA_DIR / 'dynamic' / del_tag / f'pct_{del_start + i:03d}' / tdef.csv_name}'"
                for i in range(SLICES_PER_STEP)) + "]"
            parts.append(f"CREATE OR REPLACE TEMP TABLE _del_{short} AS "
                         f"SELECT * FROM read_csv({del_list}, header=true, columns={{{colspec}}});")
        else:
            parts.append(f"CREATE OR REPLACE TEMP TABLE _del_{short} AS SELECT * FROM _ins_{short} LIMIT 0;")
    return "\n".join(parts)


def base_insert_sql():
    return "\n".join(f"INSERT INTO {tdef.fqn} SELECT * FROM _ins_{STAGE_SHORT[fqn]};"
                     for fqn, tdef in sorted(dynamic_tables().items()))


def base_delete_sql():
    parts = []
    for fqn, tdef in sorted(dynamic_tables().items()):
        cond = " AND ".join(f"t.{pk} = dk.{pk}" for pk in tdef.pk_columns)
        parts.append(f"DELETE FROM {tdef.fqn} AS t USING _del_{STAGE_SHORT[fqn]} AS dk WHERE {cond};")
    return "\n".join(parts)


def build_query_insert(method, qname, dtl_table, sum_table):
    """The fixed qN_count.sql turned into an accumulate-only INSERT. recompute
    reads the CTE query; the view-based methods read the shared query file with
    the nine view names rebound to this method's suffix (_lv / _mv / _cw)."""
    suffix = {"logical_views": "_lv", "ivm": "_mv", "crown": "_cw"}.get(method)
    if method == "recompute":
        sql = strip_comments(read_sql(f"sql/duckdb/recompute/{qname}_count.sql"))
    else:
        sql = strip_comments(read_sql(f"sql/duckdb/query/{qname}_count.sql"))
        if suffix != "_mv":
            for vname in MV_NAMES:
                sql = sql.replace(vname, vname.replace("_mv", suffix))
    target = dtl_table if qname in ("q1", "q2") else sum_table
    pk_col = "id" if qname in ("q1", "q2") else "head_id"

    sql = sql.replace("SELECT COUNT(*) AS cnt FROM (", "SELECT * FROM (")
    sql = sql.replace(") AS q;",
        f") AS _new WHERE NOT EXISTS (SELECT 1 FROM {target} _t"
        f" WHERE _t.{pk_col} = CAST(_new.{pk_col} AS VARCHAR)"
        f" AND _t.logical_is_deleted = _new.logical_is_deleted);")
    sql = sql.replace("s000_dwt_hws_iao.dwd_billing_in_transit_dtl_t_05", dtl_table)
    sql = sql.replace("s000_dwt_hws_iao.dwd_billing_in_transit_t_05", sum_table)

    cte_prefix = ""
    if suffix in ("_lv", "_cw") and qname == "q2":
        # DuckDB plans the OR-connected correlated NOT EXISTS over views as
        # delim joins that re-expand the view chain; pre-materialize the view
        # id-sets as CTEs (identical result, hash mark-joins instead).
        for view, cte in ((f"approval_temp{suffix}", "_appr_ids"),
                          (f"send_temp{suffix}", "_send_ids"),
                          (f"countersign_temp{suffix}", "_cs_ids")):
            sql = sql.replace(
                f"NOT EXISTS (SELECT 1 FROM {view} oa WHERE oa.logical_is_deleted_del IS FALSE AND oa.id = fact_t.id)",
                f"NOT EXISTS (SELECT 1 FROM {cte} oa WHERE oa.id = fact_t.id)")
        cte_prefix = (
            f"WITH _appr_ids AS MATERIALIZED (SELECT id FROM approval_temp{suffix} WHERE logical_is_deleted_del IS FALSE),\n"
            f"     _send_ids AS MATERIALIZED (SELECT id FROM send_temp{suffix} WHERE logical_is_deleted_del IS FALSE),\n"
            f"     _cs_ids   AS MATERIALIZED (SELECT id FROM countersign_temp{suffix} WHERE logical_is_deleted_del IS FALSE)\n")
    return f"INSERT INTO {target}\n{cte_prefix}{sql}"


def maintain_sql(method, step_start, insert_tag):
    if method == "ivm":
        mv = set(MV_NAMES)
        q = lambda name: name if name in mv else f"s000_cqrs_cfs.{name}"
        return ivm_maintain.build_maintain("duckdb", q, TABLES, DATA_DIR, SLICES_PER_STEP,
                                           step_start, insert_tag, None, None, load_deltas=False)
    if method == "crown":
        return crown_maintain.duckdb_maintain_sql()
    return ""


def count_form_sql(method, qname, dtl_table, sum_table):
    """The count FORM of query qname (SELECT COUNT(*) of the current result).
    crown computes q1/q2/q3 by aggregating partial counts (no full join); the
    others count their view/table result directly. Output-table refs (q2/q3/q4)
    are rebound to this method's targets."""
    if method == "crown" and qname in ("q1", "q2", "q3"):
        return crown_maintain.crown_count_sql("duckdb", qname, dtl_table)
    if method == "recompute":
        sql = strip_comments(read_sql(f"sql/duckdb/recompute/{qname}_count.sql"))
    else:
        sql = strip_comments(read_sql(f"sql/duckdb/query/{qname}_count.sql"))
        suffix = {"logical_views": "_lv", "ivm": "_mv", "crown": "_cw"}[method]
        if suffix != "_mv":
            for v in MV_NAMES:
                sql = sql.replace(v, v.replace("_mv", suffix))
    sql = sql.replace("s000_dwt_hws_iao.dwd_billing_in_transit_dtl_t_05", dtl_table)
    sql = sql.replace("s000_dwt_hws_iao.dwd_billing_in_transit_t_05", sum_table)
    return sql


def count_sql(table):
    return f"SELECT COUNT(*) FROM {table};"


def minmax_sql(table, is_dtl):
    if is_dtl:
        return (f"SELECT MIN(id), MAX(id), MIN(application_code), MAX(application_code),"
                f" MIN(submit_date), MAX(submit_date), MIN(total_amount), MAX(total_amount) FROM {table};")
    return f"SELECT MIN(head_id), MAX(head_id), MIN(total_amount), MAX(total_amount) FROM {table};"


# ── checks ──

RESULT_KINDS = (("dtl", "s000_dwt_hws_iao.dwd_billing_In_transit_dtl_t_05", VOLATILE_COLS),
                ("sum", "s000_dwt_hws_iao.dwd_billing_In_transit_t_05",
                 VOLATILE_COLS | UNORDERED_AGG_COLS))


def multiset_diff(con, a, b):
    return con.execute(
        f"SELECT count(*) FROM (({a} EXCEPT ALL {b}) UNION ALL ({b} EXCEPT ALL {a}))").fetchone()[0]


def deep_compare(con, scenario, checks):
    for kind, tkey, excl in RESULT_KINDS:
        cols = [c.name for c in TABLES[tkey].columns if c.name not in excl]
        det = ", ".join(f'"{c}"' for c in cols)
        for m1, m2 in (("recompute", "logical_views"), ("recompute", "ivm"), ("recompute", "crown")):
            n = multiset_diff(con, f"SELECT {det} FROM {TARGET[m1][kind]}",
                              f"SELECT {det} FROM {TARGET[m2][kind]}")
            checks.append(dict(scenario=scenario, check=f"final_{kind}_{m1}_vs_{m2}", mismatches=n))
    n = multiset_diff(con, "SELECT * FROM fact_t_mv", "SELECT * FROM fact_t_cw")
    checks.append(dict(scenario=scenario, check="final_fact_ivm_vs_crown", mismatches=n))


# ── runner ──

def timed(con, metrics, scenario, step, phase, method, qname, sql):
    t0 = time.perf_counter()
    con.execute(sql)
    metrics.append(dict(scenario=scenario, step=step, phase=phase, method=method,
                        qname=qname, seconds=round(time.perf_counter() - t0, 4)))


def run_scenario(scenario):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    SCRATCH.mkdir(parents=True, exist_ok=True)
    db_path = SCRATCH / f"duckdb_{SCALE}_{scenario}.duckdb"
    if db_path.exists():
        db_path.unlink()
    con = duckdb.connect(str(db_path))
    metrics, checks = [], []
    log = open(OUT_DIR / f"{scenario}.log", "w", encoding="utf-8")

    def say(msg):
        print(f"  [{scenario}] {msg}", flush=True)
        log.write(msg + "\n"); log.flush()

    timed(con, metrics, scenario, 0, "init_base", "", "", init_base_sql(scenario))
    timed(con, metrics, scenario, 0, "analyze", "", "", "ANALYZE;")
    for m in ("logical_views", "ivm", "crown"):
        timed(con, metrics, scenario, 0, "init_method", m, "", init_method_sql(m))
    say("init done")

    plan = plan_steps(scenario)
    if MAX_STEPS is not None:
        plan = plan[:MAX_STEPS]
    mismatch_total = 0

    for pstep in plan:
        step_pct = pstep["step_pct"]
        timed(con, metrics, scenario, step_pct, "staging", "", "",
              staging_sql(pstep["step_start"], pstep["insert_tag"], pstep["do_delete"],
                          pstep["del_start"], pstep["del_tag"]))
        timed(con, metrics, scenario, step_pct, "base_insert", "", "", base_insert_sql())
        if pstep["do_delete"]:
            timed(con, metrics, scenario, step_pct, "base_delete", "", "", base_delete_sql())

        step_res = {}
        cf_res = {}
        for method in METHODS:
            # fence deferred storage work so each method's timings are its own
            timed(con, metrics, scenario, step_pct, "checkpoint", method, "", "CHECKPOINT;")
            dtl, sm = TARGET[method]["dtl"], TARGET[method]["sum"]
            if method in ("ivm", "crown"):
                timed(con, metrics, scenario, step_pct, "maintain", method, "",
                      maintain_sql(method, pstep["step_start"], pstep["insert_tag"]))
            for qname in ["q1", "q2", "q3", "q4"]:
                tbl = dtl if qname in ("q1", "q2") else sm
                # accumulate INSERT: build the output tables (feeds q2/q3/q4)
                timed(con, metrics, scenario, step_pct, "query", method, qname,
                      build_query_insert(method, qname, dtl, sm))
                cnt = con.execute(count_sql(tbl)).fetchone()[0]
                mm = con.execute(minmax_sql(tbl, qname in ("q1", "q2"))).fetchone()
                step_res[(method, qname)] = (cnt, mm)
                # count form: the current-result count. crown computes it by
                # aggregating partial counts (no full-join materialize); the
                # others count their view/table result the naive way.
                t0 = time.perf_counter()
                cf = con.execute(count_form_sql(method, qname, dtl, sm)).fetchone()[0]
                metrics.append(dict(scenario=scenario, step=step_pct, phase="count_query",
                                    method=method, qname=qname,
                                    seconds=round(time.perf_counter() - t0, 4)))
                cf_res[(method, qname)] = cf

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
                    checks.append(dict(scenario=scenario,
                                       check=f"step{step_pct}_{qname}_recompute_vs_{m}",
                                       mismatches=1, detail=f"{ref} != {step_res[(m, qname)]}"))
        counts = " ".join(f"{q}={step_res[('recompute', q)][0]}" for q in ["q1", "q2", "q3", "q4"])
        say(f"step {step_pct:>3}%  {'ok ' if step_ok else 'MISMATCH'} {counts}")

    deep_compare(con, scenario, checks)
    final = [c for c in checks if c["check"].startswith("final_")]
    say("final multiset comparisons: " +
        ", ".join(f"{c['check'].replace('final_', '')}={c['mismatches']}" for c in final))
    con.close()
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
    print(f"=== DuckDB: scale={SCALE}, scenarios={scenarios} ===", flush=True)
    print(f"    data: {DATA_DIR}\n    out:  {OUT_DIR}", flush=True)
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
