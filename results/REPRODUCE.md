# Reproducing these results

These `results/` were produced by the pipeline below. All four methods produce
**identical query results** at every step; the numbers are timings only.

## Configuration

| | |
|---|---|
| Data seed | **20260715** (the generator default) |
| Scale factor | **0.1** |
| Steps | 20 (5% slide, 10% window) |
| Scenarios | insertion_only, sliding_window, preloaded_replacement_sliding |
| Methods | recompute, logical_views, ivm, crown |
| Python | 3.12 |
| DuckDB | Python `duckdb` 1.5.4 (CLI v1.5.0 for the standalone scripts) |
| openGauss | openGauss-lite 7.0.0-RC3 |
| openGauss session | `query_dop=32`, `enable_nestloop=off` for the measured queries |

## Commands

```bash
pip install -r requirements.txt
python3 runner/generate_data.py --scale 0.1 --seed 20260715   # deterministic; ~2.2 GB

python3 run_duckdb.py    --scale 0.1        # -> results/duckdb/scale_0.1/
python3 run_opengauss.py --scale 0.1        # -> results/opengauss/scale_0.1/  (needs gsql)

python3 summarize.py results/duckdb/scale_0.1
python3 summarize.py results/opengauss/scale_0.1
```

Regenerating with the same seed and scale yields byte-identical data and the
same query results. Timings will differ with hardware/server configuration.

## Correctness

Both runners assert cross-method result equality at every step and compare the
accumulated detail/summary tables (and `fact_t`) as multisets at the end:
**42/42 checks pass (21 per engine), 0 differing rows.** See each
`checks.csv`.

## Result files

Per engine under `results/<engine>/scale_0.1/`:

- `metrics.csv` — per-region timings (`scenario, step, phase, method, qname, seconds`)
- `checks.csv` — correctness checks (`mismatches` is 0 throughout)
- `report.md` — per-scenario cost tables (from `summarize.py`)
- `<scenario>.log` — per-step run log

## Cost summary (per-step means, seconds; mnt = maintenance, qry = q1–q4)

Maintenance is incremental only for `ivm` and `crown` (`recompute` /
`logical_views` recompute at query time, so their cost is all in `qry`).

### DuckDB

| scenario | recompute qry | logical_views qry | ivm mnt / qry | crown mnt / qry |
|---|---|---|---|---|
| insertion_only | 2.03 | 2.13 | 1.95 / 2.43 | 0.31 / 2.21 |
| sliding_window | 0.38 | 0.37 | 0.56 / 0.21 | 0.49 / 0.32 |
| preloaded_replacement_sliding | 4.89 | 5.12 | 3.47 / 5.78 | 0.54 / 5.54 |

### openGauss

| scenario | recompute qry | logical_views qry | ivm mnt / qry | crown mnt / qry |
|---|---|---|---|---|
| insertion_only | 46.61 | 21.98 | 6.54 / 9.03 | 1.14 / 18.93 |
| sliding_window | 1.08 | 1.13 | 2.37 / 0.30 | 1.65 / 0.44 |
| preloaded_replacement_sliding | 112.20 | 53.04 | 11.09 / 9.64 | 2.39 / 44.69 |

Across both engines, `crown` maintenance is markedly cheaper than `ivm` in the
insert-dominated scenarios (e.g. openGauss preloaded: 2.4 s vs 11.1 s per step)
and comparable in the FIFO sliding window; `ivm`'s materialized tables give it
the cheapest query side, while `crown` stays well below full recomputation.
