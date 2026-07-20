#!/usr/bin/env python3
"""Build a report.md from a runner's results directory (metrics.csv + checks.csv).

Usage: python3 summarize.py <results_dir>
e.g.   python3 summarize.py results/duckdb/scale_0.1
"""

import csv
import sys
from collections import defaultdict
from pathlib import Path

res_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "results/duckdb/scale_0.1")
metrics = list(csv.DictReader(open(res_dir / "metrics.csv", encoding="utf-8")))
checks = list(csv.DictReader(open(res_dir / "checks.csv", encoding="utf-8")))
for m in metrics:
    m["seconds"] = float(m["seconds"])
    m["step"] = int(m["step"])

order = ["insertion_only", "sliding_window", "preloaded_replacement_sliding"]
scenarios = sorted({m["scenario"] for m in metrics},
                   key=lambda s: order.index(s) if s in order else 99)
METHODS = ["recompute", "logical_views", "ivm", "crown"]
Q = ["q1", "q2", "q3", "q4"]

out = []
w = out.append
w(f"# Benchmark report — {res_dir}\n")
w("Timings in seconds. `maintain` = incremental maintenance per step "
  "(recompute/logical_views have none). `query qN` = the qN accumulate INSERT "
  "per step. Shared costs (staging, base INSERT/DELETE, ANALYZE, checkpoint "
  "fences) are reported separately, not attributed to any method.\n")

step_fail = [c for c in checks if not c["check"].startswith("final_") and int(c["mismatches"])]
final_bad = [c for c in checks if c["check"].startswith("final_") and int(c["mismatches"])]
w("## Correctness\n")
w(f"- Per-step count + min/max agreement (q1-q4, all methods vs recompute): "
  f"**{'all pass' if not step_fail else f'{len(step_fail)} FAILURES'}**")
w(f"- Final multiset comparison of accumulated outputs (deterministic columns) "
  f"and fact_t (ivm vs crown): "
  f"**{'0 differing rows in all comparisons' if not final_bad else 'FAILURES: ' + str(final_bad)}**\n")

for sc in scenarios:
    ms = [m for m in metrics if m["scenario"] == sc]
    steps = sorted({m["step"] for m in ms if m["step"] > 0})
    n = len(steps)
    w(f"\n## {sc}  ({n} steps)\n")

    init = defaultdict(float)
    for m in ms:
        if m["phase"] in ("init_method", "init_index"):
            init[m["method"]] += m["seconds"]
    shared = defaultdict(float)
    for m in ms:
        if m["phase"] in ("staging", "base_insert", "base_delete", "checkpoint",
                          "analyze", "preload"):
            shared[m["phase"]] += m["seconds"]
    extras = "".join(f", {k} {shared[k]:.1f}s" for k in ("checkpoint", "analyze", "preload")
                     if shared[k] > 0)
    w(f"Shared costs: staging {shared['staging']:.1f}s, base_insert {shared['base_insert']:.1f}s, "
      f"base_delete {shared['base_delete']:.1f}s{extras}. "
      f"Method init (incl. indexes): "
      + ", ".join(f"{m} {init.get(m, 0):.2f}s" for m in ("logical_views", "ivm", "crown")) + ".\n")

    agg = defaultdict(float)
    for m in ms:
        if m["phase"] == "maintain":
            agg[(m["method"], "maintain")] += m["seconds"]
        elif m["phase"] == "query":
            agg[(m["method"], m["qname"])] += m["seconds"]
        elif m["phase"] == "count_query":
            agg[(m["method"], "cf_" + m["qname"])] += m["seconds"]

    per = lambda v: v / n if n else 0
    w("Accumulate-INSERT cost (builds the detail/summary output tables):\n")
    w("| method | maintain/step | q1 | q2 | q3 | q4 | queries/step | maintain+queries/step |")
    w("|---|---|---|---|---|---|---|---|")
    for meth in METHODS:
        mt = agg[(meth, "maintain")]
        qs = [agg[(meth, q)] for q in Q]
        qt = sum(qs)
        w(f"| {meth} | {per(mt):.3f} | " + " | ".join(f"{per(x):.3f}" for x in qs) +
          f" | {per(qt):.3f} | {per(mt + qt):.3f} |")

    if any(m["phase"] == "count_query" for m in ms):
        w("\nCount-form cost (COUNT of the current result; crown aggregates "
          "partial counts instead of materializing the join):\n")
        w("| method | cf_q1 | cf_q2 | cf_q3 | cf_q4 | count-form/step |")
        w("|---|---|---|---|---|---|")
        for meth in METHODS:
            cfs = [agg[(meth, "cf_" + q)] for q in Q]
            w(f"| {meth} | " + " | ".join(f"{per(x):.3f}" for x in cfs) +
              f" | {per(sum(cfs)):.3f} |")

    w("")
    for meth in ("ivm", "crown"):
        pl = sorted(m["seconds"] for m in ms if m["phase"] == "maintain" and m["method"] == meth)
        if pl:
            w(f"- {meth} maintain per step: min {pl[0]:.3f}s, median {pl[len(pl)//2]:.3f}s, max {pl[-1]:.3f}s")

print("\n".join(out))
(res_dir / "report.md").write_text("\n".join(out) + "\n", encoding="utf-8")
