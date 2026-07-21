#!/usr/bin/env python3
"""Emit one self-contained, timed SQL script per method.

Each generated file simulates a single method (recompute / logical_views /
ivm / crown) end-to-end for one scenario: schema + tables + static/preload,
the method's persistent objects, then the 20 update steps (slice staging,
base INSERT/DELETE, maintenance, the four q1-q4 accumulate INSERTs, and a
COUNT + MIN/MAX after each). Submit a file directly to the engine and capture
stdout; `parse_output.py` turns that capture into timing and result CSVs.

Every timed region is bracketed by marker rows so the parser can attribute
per-statement timings and capture query outputs:

    SELECT '@@JOB5@@|B|<scenario>|<phase>|<method>|<qname>|<step>';
    <one or more statements>
    SELECT '@@JOB5@@|E|<scenario>|<phase>|<method>|<qname>|<step>';

The SQL itself is built by the same functions the runners use (run_duckdb.py /
run_opengauss.py), so the generated scripts execute exactly what the runners
execute — only the driver differs.

Two path modes:
  --portable (default): emit scale-agnostic scripts with `__DATA_ROOT__` and
      `__SCALE__` placeholders, into generated_sql/<engine>/. These are the
      committed artifacts; substitute the two tokens to run (see below).
  --absolute: bake in the concrete JOB5_DATA_DIR path and --scale, into
      generated_sql/<engine>/scale_<sf>/. Directly runnable locally; not
      committed (gitignored).

Usage:
  python3 gen_sql.py --engine duckdb                          # portable, committed form
  python3 gen_sql.py --engine opengauss --schema-prefix exp
  python3 gen_sql.py --engine duckdb --absolute --scale 0.1   # local runnable form

Run a committed (portable) file by substituting the two tokens:
  sed -e 's#__DATA_ROOT__#/abs/path/to/data#g' -e 's#__SCALE__#0.1#g' \\
      generated_sql/duckdb/insertion_only__crown.sql | duckdb > out.log
  sed -e 's#__DATA_ROOT__#/abs/path/to/data#g' -e 's#__SCALE__#0.1#g' \\
      generated_sql/opengauss/insertion_only__crown.sql > /tmp/f.sql
  gsql -t -A -f /tmp/f.sql > out.log
then:  python3 parse_output.py out.log
"""

import argparse
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_DIR))

QUERIES = ["q1", "q2", "q3", "q4"]


def _mark(kind, scenario, phase, method, qname, step):
    return f"SELECT '@@JOB5@@|{kind}|{scenario}|{phase}|{method}|{qname}|{step}';\n"


def _region(f, scenario, phase, method, qname, step, sql):
    f.write(_mark("B", scenario, phase, method, qname, step))
    f.write(sql.rstrip())
    if not sql.rstrip().endswith(";"):
        f.write(";")
    f.write("\n")
    f.write(_mark("E", scenario, phase, method, qname, step))


# ── DuckDB ──

def gen_duckdb(scale, scenarios, methods, out_dir):
    import run_duckdb as R
    R.configure(scale)
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for scenario in scenarios:
        for method in methods:
            path = out_dir / f"{scenario}__{method}.sql"
            with open(path, "w", encoding="utf-8") as f:
                f.write(f"-- DuckDB | scenario={scenario} | method={method} | scale={scale}\n")
                f.write(".mode csv\n.headers off\n.timer on\n")
                _region(f, scenario, "init_base", method, "", 0, R.init_base_sql(scenario))
                _region(f, scenario, "analyze", method, "", 0, "ANALYZE;")
                init_m = R.init_method_sql(method)
                if init_m.strip():
                    _region(f, scenario, "init_method", method, "", 0, init_m)
                dtl, sm = R.TARGET[method]["dtl"], R.TARGET[method]["sum"]
                for p in R.plan_steps(scenario):
                    sp_ = p["step_pct"]
                    _region(f, scenario, "staging", method, "", sp_,
                            R.staging_sql(p["step_start"], p["insert_tag"], p["do_delete"],
                                          p["del_start"], p["del_tag"]))
                    _region(f, scenario, "base_insert", method, "", sp_, R.base_insert_sql())
                    if p["do_delete"]:
                        _region(f, scenario, "base_delete", method, "", sp_, R.base_delete_sql())
                    if method in ("ivm", "crown"):
                        _region(f, scenario, "maintain", method, "", sp_,
                                R.maintain_sql(method, p["step_start"], p["insert_tag"]))
                    for q in QUERIES:
                        tbl = dtl if q in ("q1", "q2") else sm
                        _region(f, scenario, "query", method, q, sp_, R.build_query_insert(method, q, dtl, sm))
                        _region(f, scenario, "count", method, q, sp_, R.count_form_sql(method, q, dtl, sm))
                        _region(f, scenario, "minmax", method, q, sp_, R.minmax_sql(tbl, q in ("q1", "q2")))
            written.append(path)
    return written


# ── openGauss ──

def gen_opengauss(scale, scenarios, methods, out_dir, schema_prefix):
    import run_opengauss as R
    R.configure(scale)
    from maintain import crown_maintain
    out_dir.mkdir(parents=True, exist_ok=True)
    schema_map = {"insertion_only": f"{schema_prefix}_ins",
                  "sliding_window": f"{schema_prefix}_sw",
                  "preloaded_replacement_sliding": f"{schema_prefix}_prs"}
    written = []
    for scenario in scenarios:
        schema = schema_map[scenario]
        for method in methods:
            path = out_dir / f"{scenario}__{method}.sql"
            with open(path, "w", encoding="utf-8") as f:
                f.write(f"-- openGauss | scenario={scenario} | method={method} | scale={scale} | schema={schema}\n")
                f.write("\\timing on\n")
                f.write(f"DROP SCHEMA IF EXISTS {schema} CASCADE;\n")
                _region(f, scenario, "init_base", method, "", 0, R.build_init_sql(schema, scenario))
                if method == "logical_views":
                    _region(f, scenario, "init_method", method, "", 0, R.build_lv_init_sql(schema))
                elif method == "ivm":
                    _region(f, scenario, "init_method", method, "", 0, R.build_ivm_init_sql(schema))
                    _region(f, scenario, "init_index", method, "", 0, R.build_mv_index_sql(schema))
                elif method == "crown":
                    _region(f, scenario, "init_method", method, "", 0,
                            R.sp(schema) + crown_maintain.opengauss_state_init_sql())
                    _region(f, scenario, "init_index", method, "", 0,
                            R.sp(schema) + crown_maintain.opengauss_index_sql(schema))
                    lv_text = R.read_sql("sql/opengauss/logical_views/init.sql")
                    _region(f, scenario, "init_views", method, "", 0,
                            R.sp(schema) + crown_maintain.opengauss_assembly_views_sql(lv_text, schema))
                    _region(f, scenario, "init_index", method, "", 0,
                            R.sp(schema) + crown_maintain.fact_ids_init_sql())
                # one post-init ANALYZE of all relevant tables in this schema
                an_tables = [t.table for _, t in sorted(R.static_tables().items())]
                if scenario == "preloaded_replacement_sliding":
                    an_tables += [t.table for _, t in sorted(R.dynamic_tables().items())]
                an_tables += [f"mlog_ins_{R.STAGE_SHORT[fq]}" for fq in sorted(R.dynamic_tables())]
                an_tables += [f"mlog_del_{R.STAGE_SHORT[fq]}" for fq in sorted(R.dynamic_tables())]
                an_tables += [a["dtl"] for a in R.TARGET.values()] + [a["sum"] for a in R.TARGET.values()]
                if method == "ivm":
                    an_tables += R.MV_NAMES
                elif method == "crown":
                    an_tables += R.CROWN_TABLES
                _region(f, scenario, "analyze", method, "", 0, R.analyze_sql(schema, an_tables))

                dtl, sm = R.TARGET[method]["dtl"], R.TARGET[method]["sum"]
                for p in R.plan_steps(scenario):
                    sp_ = p["step_pct"]
                    _region(f, scenario, "staging", method, "", sp_,
                            R.build_staging_sql(schema, p["step_start"], p["insert_tag"],
                                                p["del_start"] if p["do_delete"] else None,
                                                p["del_tag"] if p["do_delete"] else None))
                    _region(f, scenario, "base_insert", method, "", sp_, R.build_insert_sql(schema))
                    if p["do_delete"]:
                        _region(f, scenario, "base_delete", method, "", sp_, R.build_delete_sql(schema))
                    if method == "ivm":
                        _region(f, scenario, "maintain", method, "", sp_,
                                R.build_ivm_maintain(schema, p["step_start"], p["insert_tag"],
                                                     p["del_start"] if p["do_delete"] else None,
                                                     p["del_tag"] if p["do_delete"] else None))
                    elif method == "crown":
                        _region(f, scenario, "maintain", method, "", sp_,
                                R.sp(schema) + crown_maintain.opengauss_maintain_sql()
                                + "\n" + crown_maintain.fact_ids_maintain_sql("opengauss"))
                    for q in QUERIES:
                        tbl = dtl if q in ("q1", "q2") else sm
                        _region(f, scenario, "query", method, q, sp_, R.build_query(schema, method, q, dtl, sm))
                        _region(f, scenario, "count", method, q, sp_, R.count_form_sql(schema, method, q, dtl, sm))
                        _region(f, scenario, "minmax", method, q, sp_,
                                R.build_minmax_query(schema, tbl, q in ("q1", "q2")))
            written.append(path)
    return written


def main():
    import os
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", choices=["duckdb", "opengauss"], required=True)
    ap.add_argument("--scale", default="0.1")
    ap.add_argument("--scenarios", default="insertion_only,sliding_window,preloaded_replacement_sliding")
    ap.add_argument("--methods", default="recompute,logical_views,ivm,crown")
    ap.add_argument("--schema-prefix", default="exp")
    ap.add_argument("--absolute", action="store_true",
                    help="bake in the concrete data path + scale (local, not committed)")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    scenarios = [s.strip() for s in args.scenarios.split(",") if s.strip()]
    methods = [m.strip() for m in args.methods.split(",") if m.strip()]
    out_root = Path(args.out) if args.out else PROJECT_DIR / "generated_sql"

    if args.absolute:
        scale = args.scale
        out_dir = out_root / args.engine / f"scale_{scale}"
    else:
        # portable: tokens for data root + scale; scale-agnostic committed form
        os.environ["JOB5_DATA_DIR"] = "__DATA_ROOT__"
        scale = "__SCALE__"
        out_dir = out_root / args.engine

    if args.engine == "duckdb":
        files = gen_duckdb(scale, scenarios, methods, out_dir)
    else:
        files = gen_opengauss(scale, scenarios, methods, out_dir, args.schema_prefix)

    print(f"wrote {len(files)} SQL files under {out_dir} "
          f"({'absolute paths' if args.absolute else 'portable __DATA_ROOT__/__SCALE__ tokens'}):")
    for p in files:
        print(f"  {p.name}  ({p.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
