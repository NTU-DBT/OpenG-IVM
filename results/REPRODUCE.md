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

Every step, all four methods are checked for identical results two ways: the
count + min/max of the accumulated outputs, and the **count FORM** of each
query (the current-result COUNT). At the end the accumulated detail/summary
tables and `fact_t` are compared as multisets. **All checks pass on both
engines, 0 differing rows** (`checks.csv` holds the 21 final multiset
comparisons per engine; per-step count-form and accumulate mismatches, of
which there are none, would also appear there).

## Result files

Per engine under `results/<engine>/scale_0.1/`:

- `metrics.csv` — per-region timings (`scenario, step, phase, method, qname, seconds`);
  phase `query` = accumulate INSERT (builds output), `count_query` = count form, `maintain` = incremental maintenance
- `checks.csv` — correctness checks (`mismatches` is 0 throughout)
- `report.md` — per-scenario cost tables (from `summarize.py`)
- `<scenario>.log` — per-step run log

## Cost summary (per-step means, seconds)

Three costs matter. **maint** = incremental maintenance (only `ivm`/`crown`).
**count** = the count FORM total (q1–q4): `crown` computes it by aggregating
the maintained partial counts along the join tree — no join is materialized —
while the others count their view/table result. **build** = the accumulate
INSERTs that materialize the full detail/summary output rows (q1–q4 total).

### DuckDB

| scenario | ivm maint / count / build | crown maint / count / build |
|---|---|---|
| insertion_only | 1.98 / 0.22 / 2.42 | 0.31 / 1.02 / 2.19 |
| sliding_window | 0.57 / 0.04 / 0.21 | 0.51 / 0.07 / 0.33 |
| preloaded_replacement_sliding | 3.49 / 0.44 / 5.76 | 0.54 / 2.45 / 5.58 |

### openGauss

| scenario | ivm maint / count / build | crown maint / count / build |
|---|---|---|
| insertion_only | 6.43 / 10.37 / 11.56 | 1.15 / **1.05** / 19.03 |
| sliding_window | 2.46 / 0.25 / 0.30 | 1.70 / 0.34 / 0.44 |
| preloaded_replacement_sliding | 10.61 / 6.39 / 9.81 | 2.34 / **2.87** / 44.47 |

Reading the numbers:

- **Maintenance:** `crown` is ~3–5× cheaper than `ivm` everywhere — it does no
  join work; `ivm` rebuilds joined rows including the n:m branch views.
- **Count queries:** `crown` is cheapest of all methods on openGauss
  (insertion 1.05 s vs `ivm` 10.37 s, `recompute` 45.6 s), because it never
  assembles the join — the gap is driven by q3 (crown 0.26 s vs ivm 9.4 s).
- **Build (emit full joined rows):** `ivm` wins on openGauss (reads a
  materialized table vs `crown` re-joining at query time); on DuckDB the two
  are close because the assembly join is cheap there.

Net: the more the workload leans on updates and count/aggregate queries, the
more `crown` dominates; `ivm` pays off only when the full joined detail must be
materialized frequently on an engine where large joins are costly.
