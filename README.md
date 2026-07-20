# Job 5 Streaming Query-Maintenance Benchmark

Incremental view maintenance for the Job 5 workload — a nine-view materialized
pipeline (`docs/` describes the workload and the CROWN design) — evaluated
under streaming updates with **four maintenance methods** compared for
correctness and cost on **DuckDB** and **openGauss**:

| Method | What it does |
|---|---|
| `recompute` | Full recomputation of every query at each step; no persistent state. |
| `logical_views` | The nine views declared once as ordinary SQL views; each query expands them at run time. |
| `ivm` | Physical materialized tables maintained by delta logic translated from the workload's `job5_ivm.sql` (`maintain/ivm_maintain.py`). |
| `crown` | **Change Propagation Without Joins** (Wang, Hu, Dai, Yi — PVLDB 16(5), 2023): maintenance propagates deltas through semi-join and projection views with derivation counting and never materializes a join; final results are assembled at query time by one SQL join over the maintained partial results (`maintain/crown_maintain.py`, `docs/crown_maintenance_plan.md`). |

Each run drives three update scenarios (`insertion_only`, `sliding_window`,
`preloaded_replacement_sliding`) for 20 steps of 5% each, runs the four
benchmark queries (q1–q4) at every step, records per-phase timings, and
**checks that all four methods produce identical query results** at every step
(count + min/max) and as multisets over the accumulated outputs at the end.

## Layout

```
run_duckdb.py          # DuckDB runner  (all 4 methods, correctness checks, metrics)
run_opengauss.py       # openGauss runner (same)
gen_sql.py             # emit one standalone, timed SQL script per method
parse_output.py        # parse a script's captured output into timing + result CSVs
summarize.py           # turn a results dir into report.md
maintain/
  ivm_maintain.py      # IVM delta maintenance (both dialects)
  crown_maintain.py    # CROWN state + assembly + maintenance (both dialects)
runner/
  data_model.py        # table schemas, keys, static/dynamic classification
  generate_data.py     # deterministic CSV data generator
  config.py            # generation/experiment parameters
sql/
  duckdb/  {init,runtime,recompute,logical_views,ivm,query}/*.sql
  opengauss/{init,runtime,recompute,logical_views,ivm,query}/*.sql
docs/
  crown_maintenance_plan.md   # the CROWN design + executed verification
```

Data and results are **not** included; generate/produce them as below.

## Requirements

- Python 3.10+ and `pip install -r requirements.txt` (just `duckdb`).
- For the openGauss runner: a running openGauss server and the `gsql` client
  on `PATH` (or set `JOB5_GSQL` to its path). Connection settings come from
  gsql's own environment (see `.env.example`).

## 1. Generate data

Data is deterministic from a seed. Each scale factor produces a `data/` tree
(`static/`, `scale_<sf>/dynamic/{base,extra}/pct_001..100/`). Approx sizes:
scale 0.001 ≈ 40 MB, scale 0.1 ≈ 2 GB, scale 1.0 ≈ 20 GB.

```bash
pip install -r requirements.txt
python3 runner/generate_data.py --scale 0.1 --seed 20260715   # -> ./data/scale_0.1 and ./data/static
```

**Reproducibility — the committed results use `--seed 20260715` (the default).**
Regenerating with the same seed and scale reproduces byte-identical data, and
hence the same query results; see `results/REPRODUCE.md`. Generate the small
scale first (`--scale 0.001`) for a quick end-to-end check. By default runners
read `./data`; point elsewhere with `JOB5_DATA_DIR`.

## 2. Run

```bash
# DuckDB — all methods, all scenarios, scale 0.1
python3 run_duckdb.py --scale 0.1

# openGauss — same (server must be running; gsql on PATH or set JOB5_GSQL)
python3 run_opengauss.py --scale 0.1

# subset / quick check
python3 run_duckdb.py --scale 0.001 --scenarios insertion_only --max-steps 3
```

Each runner prints per-step correctness (`ok`/`MISMATCH`) and exits non-zero if
any method disagrees with `recompute`. Metrics and per-scenario logs are
written under `results/<engine>/scale_<sf>/`.

Useful environment variables:

| var | meaning | default |
|---|---|---|
| `JOB5_DATA_DIR` | data root (containing `static/` and `scale_*/`) | `./data` |
| `JOB5_SCRATCH` | scratch dir for DuckDB DB files / gsql temp SQL | `./.scratch` |
| `JOB5_GSQL` | openGauss client command | `gsql` |
| `JOB5_SCHEMA_PREFIX` | openGauss schema prefix (`<p>_ins`, `<p>_sw`, `<p>_prs`) | `exp` |
| `QUERY_DOP` | openGauss intra-query parallelism | `32` |

The openGauss runner creates one schema per scenario and drops/recreates it at
the start of each run.

## Alternative: standalone SQL scripts per method

To submit SQL directly to a database (no Python driver in the loop) and parse
the output afterwards, use the committed per-method scripts in
[`generated_sql/`](generated_sql/) — one self-contained, timed script per
method × scenario, for each engine. They are portable: substitute the
`__DATA_ROOT__` and `__SCALE__` placeholders, submit, and parse:

```bash
# DuckDB
sed -e 's#__DATA_ROOT__#'"$PWD"'/data#g' -e 's#__SCALE__#0.1#g' \
    generated_sql/duckdb/insertion_only__crown.sql | duckdb > crown.log
python3 parse_output.py crown.log        # writes metrics.csv + results.csv next to the log

# openGauss (tuples-only, unaligned so results parse cleanly)
sed -e 's#__DATA_ROOT__#/abs/path/to/data#g' -e 's#__SCALE__#0.1#g' \
    generated_sql/opengauss/insertion_only__crown.sql > /tmp/f.sql
gsql -t -A -f /tmp/f.sql > crown.log
python3 parse_output.py crown.log

# parse many logs at once (or a directory) to compare methods
python3 parse_output.py path/to/logs/
```

`parse_output.py` writes `metrics.csv` (scenario, step, phase, method, qname,
seconds — maintenance and per-query timings, summed per timed region) and
`results.csv` (the COUNT and MIN/MAX outputs), and prints per-method per-step
totals. Comparing `results.csv` across methods is the correctness check when
running this way. Regenerate the scripts with `python3 gen_sql.py --engine
duckdb` / `--engine opengauss`; see [`generated_sql/README.md`](generated_sql/README.md).

## 3. Summarize

```bash
python3 summarize.py results/duckdb/scale_0.1      # writes report.md in that dir
python3 summarize.py results/opengauss/scale_0.1
```

`report.md` reports, per scenario: correctness status, per-step maintenance
cost for `ivm` and `crown`, and per-step query cost for all four methods
(shared staging / base-DML / analyze costs listed separately).

## Reproducing the comparison

1. `python3 runner/generate_data.py --scale 0.1`
2. `python3 run_duckdb.py --scale 0.1 && python3 summarize.py results/duckdb/scale_0.1`
3. `python3 run_opengauss.py --scale 0.1 && python3 summarize.py results/opengauss/scale_0.1`

Both runners assert cross-method result equality at every step, so a clean exit
(code 0) with `ALL RESULTS IDENTICAL` is itself the correctness result; the
cost tables come from `summarize.py`.

## Notes

- Volatile columns (`NOW()`-derived timestamps, `_hoodie_event_time`) and
  order-sensitive `string_agg` columns are excluded from cross-method equality
  checks — they are not deterministic across methods/runs by construction. All
  other columns must match exactly.
- The CROWN method handles operations outside its native class (MIN/MAX under
  deletion, outer joins) as in-framework extensions without a theoretical
  guarantee; see `docs/crown_maintenance_plan.md`.
