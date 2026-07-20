# Generated SQL scripts

One self-contained, timed SQL script per method × scenario, for each engine —
produced by `../gen_sql.py`. Each script runs a single method end-to-end for
one scenario (schema + tables + static/preload, the method's persistent
objects, then the 20 update steps with the four q1–q4 queries), with
`@@JOB5@@|B|…` / `@@JOB5@@|E|…` markers around every timed region. Each step
has, per query, a `query` region (accumulate INSERT that builds the output), a
`count` region (the count FORM — the crown method aggregates maintained partial
counts instead of materializing the join), and a `minmax` region.

```
duckdb/    <scenario>__<method>.sql   (recompute | logical_views | ivm | crown)
opengauss/ <scenario>__<method>.sql
```

These committed scripts are **portable**: data paths use two placeholders,
`__DATA_ROOT__` (the data directory holding `static/` and `scale_*/`) and
`__SCALE__` (e.g. `0.1`). Substitute both, then submit and parse:

```bash
# DuckDB
sed -e 's#__DATA_ROOT__#/abs/path/to/data#g' -e 's#__SCALE__#0.1#g' \
    duckdb/insertion_only__crown.sql | duckdb > out.log
python3 ../parse_output.py out.log        # -> metrics.csv + results.csv

# openGauss (tuples-only, unaligned)
sed -e 's#__DATA_ROOT__#/abs/path/to/data#g' -e 's#__SCALE__#0.1#g' \
    opengauss/insertion_only__crown.sql > /tmp/f.sql
gsql -t -A -f /tmp/f.sql > out.log
python3 ../parse_output.py out.log
```

`parse_output.py` sums the per-statement engine timings in each region and
captures the COUNT / MIN-MAX outputs. Comparing `results.csv` across the four
methods is the correctness check.

The openGauss scripts create/drop a per-scenario schema named `exp_ins` /
`exp_sw` / `exp_prs`; `sed 's#exp_#myprefix_#g'` to relocate them.

Regenerate with `python3 ../gen_sql.py --engine duckdb` (and `--engine
opengauss`). For a directly-runnable local copy with real paths baked in, use
`--absolute --scale 0.1` (written under `<engine>/scale_0.1/`, not committed).
