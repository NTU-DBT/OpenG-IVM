#!/usr/bin/env python3
"""Parse the captured stdout of a generated SQL script into timing + result CSVs.

Reads the marker-bracketed output produced by running a gen_sql.py script
(see its header) and, for every timed region, sums the per-statement engine
timings and captures the query output. Works on a single log or many
(pass several files, or a directory of *.log / *.out).

Marker rows look like:
    @@JOB5@@|B|<scenario>|<phase>|<method>|<qname>|<step>
    ... engine output + per-statement timing lines ...
    @@JOB5@@|E|<scenario>|<phase>|<method>|<qname>|<step>

Timing lines are recognized for both engines:
    DuckDB     : "Run Time (s): real 0.123 user ... sys ..."
    openGauss  : "Time: 12.345 ms"

Outputs, next to the first input (or --out DIR):
    metrics.csv  scenario, step, phase, method, qname, seconds
    results.csv  scenario, step, method, qname, form(count|minmax), value
A summary of maintenance/query totals per method is printed.

Usage:
  python3 parse_output.py [--engine auto|duckdb|opengauss] [--out DIR] <log ...>
"""

import argparse
import csv
import re
from collections import defaultdict
from pathlib import Path

DUCK_RE = re.compile(r"Run Time \(s\): real ([\d.]+)")
OG_RE = re.compile(r"^Time: ([\d.]+) ms")
B_RE = re.compile(r"@@JOB5@@\|B\|(.*)$")
E_RE = re.compile(r"@@JOB5@@\|E\|")


def _timing(line):
    m = DUCK_RE.search(line)
    if m:
        return float(m.group(1))
    m = OG_RE.match(line)
    if m:
        return float(m.group(1)) / 1000.0
    return None


def parse_stream(lines):
    """Yield (fields, seconds, results) per completed region."""
    cur = None
    timings = []
    results = []
    b_skipped = False
    for raw in lines:
        line = raw.rstrip("\r\n")
        mb = B_RE.search(line)
        if mb:
            cur = mb.group(1).split("|")   # scenario, phase, method, qname, step
            timings, results, b_skipped = [], [], False
            continue
        if cur is not None and E_RE.search(line):
            yield cur, round(sum(timings), 6), results
            cur = None
            continue
        if cur is None:
            continue
        t = _timing(line)
        if t is not None:
            if not b_skipped:      # the B-marker SELECT's own timing
                b_skipped = True
            else:
                timings.append(t)
        elif line.strip() and "@@JOB5@@" not in line:
            results.append(line.strip())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", default="auto")  # kept for clarity; detection is automatic
    ap.add_argument("--out", default=None)
    ap.add_argument("logs", nargs="+")
    args = ap.parse_args()

    paths = []
    for a in args.logs:
        p = Path(a)
        if p.is_dir():
            paths += sorted(list(p.glob("*.log")) + list(p.glob("*.out")))
        else:
            paths.append(p)

    metrics, results = [], []
    for p in paths:
        with open(p, encoding="utf-8", errors="replace") as f:
            for fields, secs, res in parse_stream(f):
                if len(fields) < 5:
                    continue
                scenario, phase, method, qname, step = fields[:5]
                metrics.append(dict(scenario=scenario, step=int(step), phase=phase,
                                    method=method, qname=qname, seconds=secs))
                if phase in ("count", "minmax") and res:
                    results.append(dict(scenario=scenario, step=int(step), method=method,
                                        qname=qname, form=phase, value=res[-1]))

    out_dir = Path(args.out) if args.out else (paths[0].parent if paths else Path("."))
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "metrics.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["scenario", "step", "phase", "method", "qname", "seconds"])
        w.writeheader(); w.writerows(metrics)
    with open(out_dir / "results.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["scenario", "step", "method", "qname", "form", "value"])
        w.writeheader(); w.writerows(results)

    # summary
    agg = defaultdict(float)
    steps = defaultdict(set)
    for m in metrics:
        if m["step"] > 0:
            steps[m["scenario"]].add(m["step"])
        if m["phase"] == "maintain":
            agg[(m["scenario"], m["method"], "maintain")] += m["seconds"]
        elif m["phase"] == "query":
            agg[(m["scenario"], m["method"], "query")] += m["seconds"]
    print(f"parsed {len(paths)} log(s): {len(metrics)} regions, {len(results)} query results")
    scen = sorted({m["scenario"] for m in metrics})
    for sc in scen:
        n = len(steps[sc]) or 1
        print(f"\n[{sc}] {n} steps — per-step totals (s):")
        print(f"  {'method':<15} {'maintain':>10} {'queries':>10}")
        for meth in ("recompute", "logical_views", "ivm", "crown"):
            mt = agg.get((sc, meth, "maintain"), 0.0)
            qt = agg.get((sc, meth, "query"), 0.0)
            if (sc, meth, "maintain") in agg or (sc, meth, "query") in agg:
                print(f"  {meth:<15} {mt / n:>10.3f} {qt / n:>10.3f}")
    print(f"\nwrote {out_dir/'metrics.csv'} and {out_dir/'results.csv'}")


if __name__ == "__main__":
    main()
