# Compute-overhead experiment (CPU time & memory)

The main benchmark (`../results/`) measures wall-clock latency per phase. This
experiment isolates the **computing overhead** of each maintenance method —
CPU seconds and peak resident memory — which is where CROWN's join-free state
is expected to pay off (no materialized n:m join to build or hold in memory).

## Method

`run_overhead.py` runs each method's full pipeline (base updates + that
method's maintenance + its q1–q4 build and count forms) in a **dedicated,
fresh, in-memory DuckDB process** per scenario, then reads that process's own
`getrusage`:

- `cpu_s` — `ru_utime + ru_stime` (CPU seconds across DuckDB's threads)
- `peak_rss_mb` — `ru_maxrss` (peak resident memory of the process)
- `state_rows` — rows held in the method's persistent state tables
  (`ivm`: the nine `*_mv`; `crown`: the `crown_*` tables; `recompute` /
  `logical_views` keep none)

A `base_only` process (base updates, no method) gives the shared baseline, so
the per-method overhead is `value − base_only` (the Δ columns in the report).

Design choices: an **in-memory** database so peak RSS reflects the method's real
footprint (a file-backed DB would spill to disk and hide it); **pinned DuckDB
threads** so CPU seconds are comparable across methods; one process per method
so CPU/RSS are cleanly attributable.

openGauss is intentionally not measured here — its client-server model puts
CPU/memory on the server across many short-lived backends, so per-method
server-side attribution is not reliable with this harness. DuckDB (one
in-process engine) gives the clean, controlled comparison. The latency
comparison for both engines is in `../results/`.

## Run

```bash
python3 overhead/run_overhead.py --scale 0.1 --threads 4
# -> overhead/results/scale_0.1/overhead.csv and report.md
```

Data is read from `JOB5_DATA_DIR` (default `./data`), same as the main runners.
