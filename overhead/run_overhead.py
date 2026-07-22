#!/usr/bin/env python3
"""Compute-overhead experiment: CPU time and peak memory per method.

The main benchmark measures wall-clock latency per phase. This experiment
isolates the *computing overhead* — CPU seconds and peak resident memory — of
each maintenance method, which is where CROWN's join-free state is expected to
pay off (no materialized n:m join to build or hold).

Method: run each method's full pipeline (base updates + that method's
maintenance + its q1-q4 build and count forms) in a **dedicated, fresh,
in-memory DuckDB process** for one scenario, then read that process's own
resource usage:
  * cpu_s      = ru_utime + ru_stime  (CPU seconds across DuckDB's threads)
  * peak_rss_mb= ru_maxrss            (peak resident memory of the process)
  * state_rows = rows held in the method's persistent state tables
                 (ivm: the 9 *_mv; crown: the crown_* tables; recompute /
                 logical_views keep none)
A `base_only` process (base updates, no method) gives the shared baseline, so
per-method overhead = value − base_only.

An in-memory database is used on purpose so peak RSS reflects the method's real
memory footprint (a file-backed DB would spill to disk and hide it). DuckDB
threads are pinned so CPU seconds are comparable across methods.

openGauss is not measured here: its client-server model puts CPU/memory on the
server across many short-lived backends, so per-method server-side attribution
is not reliable with this harness. DuckDB (single in-process engine) gives a
clean, controlled per-method comparison.

Usage:
  python3 overhead/run_overhead.py [--scale 0.1] [--scenarios ...] [--threads 4]
"""

import argparse
import csv
import multiprocessing as mp
import resource
import sys
import time
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))
sys.path.insert(0, str(PROJECT_DIR / "runner"))

METHODS = ["base_only", "recompute", "logical_views", "ivm", "crown"]


def _worker(method, scenario, scale, threads, q):
    import duckdb
    import run_duckdb as R
    from maintain import crown_maintain
    R.configure(scale)
    con = duckdb.connect(":memory:")
    con.execute(f"PRAGMA threads={threads}")
    con.execute(R.init_base_sql(scenario))
    con.execute("ANALYZE;")
    if method not in ("base_only",):
        im = R.init_method_sql(method)
        if im.strip():
            con.execute(im)
    t0 = time.perf_counter()
    for p in R.plan_steps(scenario):
        con.execute(R.staging_sql(p["step_start"], p["insert_tag"], p["do_delete"],
                                  p["del_start"], p["del_tag"]))
        con.execute(R.base_insert_sql())
        if p["do_delete"]:
            con.execute(R.base_delete_sql())
        if method in ("ivm", "crown"):
            con.execute(R.maintain_sql(method, p["step_start"], p["insert_tag"]))
        if method not in ("base_only",):
            dtl, sm = R.TARGET[method]["dtl"], R.TARGET[method]["sum"]
            for qn in ("q1", "q2", "q3", "q4"):
                con.execute(R.build_query_insert(method, qn, dtl, sm))
                con.execute(R.count_form_sql(method, qn, dtl, sm))
    wall = time.perf_counter() - t0

    state_rows = 0
    state_tables = (R.MV_NAMES if method == "ivm"
                    else crown_maintain.CROWN_TABLES if method == "crown" else [])
    for n in state_tables:
        try:
            state_rows += con.execute(f"SELECT count(*) FROM {n}").fetchone()[0]
        except Exception:
            pass
    con.close()

    ru = resource.getrusage(resource.RUSAGE_SELF)
    q.put(dict(method=method, scenario=scenario,
               cpu_s=round(ru.ru_utime + ru.ru_stime, 2),
               peak_rss_mb=round(ru.ru_maxrss / 1024.0, 1),
               wall_s=round(wall, 2),
               state_rows=state_rows))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scale", default="0.1")
    ap.add_argument("--scenarios", default="insertion_only,sliding_window,preloaded_replacement_sliding")
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    scenarios = [s.strip() for s in args.scenarios.split(",") if s.strip()]
    out_dir = Path(args.out) if args.out else PROJECT_DIR / "overhead" / "results" / f"scale_{args.scale}"
    out_dir.mkdir(parents=True, exist_ok=True)
    ctx = mp.get_context("spawn")

    rows = []
    print(f"=== overhead: scale={args.scale}, threads={args.threads}, scenarios={scenarios} ===", flush=True)
    for scenario in scenarios:
        for method in METHODS:
            q = ctx.Queue()
            proc = ctx.Process(target=_worker, args=(method, scenario, args.scale, args.threads, q))
            proc.start()
            res = q.get()
            proc.join()
            rows.append(res)
            print(f"  [{scenario}] {method:<14} cpu={res['cpu_s']:>8.2f}s "
                  f"peak_rss={res['peak_rss_mb']:>8.1f}MB wall={res['wall_s']:>8.2f}s "
                  f"state_rows={res['state_rows']}", flush=True)

    with open(out_dir / "overhead.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["scenario", "method", "cpu_s", "peak_rss_mb", "wall_s", "state_rows"])
        w.writeheader()
        w.writerows(rows)

    # summary: per-method overhead over base_only
    base = {r["scenario"]: r for r in rows if r["method"] == "base_only"}
    lines = [f"# Compute-overhead experiment — DuckDB, scale {args.scale}, threads {args.threads}\n",
             "Per method: CPU seconds (user+sys across threads), peak process RSS, and "
             "persistent state size. `base_only` = base updates with no method; the "
             "Δ columns subtract it to isolate the method's own overhead.\n"]
    for scenario in scenarios:
        b = base.get(scenario)
        lines.append(f"\n## {scenario}\n")
        lines.append("| method | CPU s | ΔCPU vs base | peak RSS MB | ΔRSS vs base | state rows |")
        lines.append("|---|---|---|---|---|---|")
        for r in [x for x in rows if x["scenario"] == scenario]:
            dcpu = f"{r['cpu_s'] - b['cpu_s']:+.2f}" if b else ""
            drss = f"{r['peak_rss_mb'] - b['peak_rss_mb']:+.1f}" if b else ""
            lines.append(f"| {r['method']} | {r['cpu_s']:.2f} | {dcpu} | "
                         f"{r['peak_rss_mb']:.1f} | {drss} | {r['state_rows']} |")
    (out_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nwrote {out_dir/'overhead.csv'} and {out_dir/'report.md'}")


if __name__ == "__main__":
    main()
