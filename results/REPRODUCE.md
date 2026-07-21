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
**count** = the count FORM total (q1–q4): `crown` aggregates the maintained
partial counts — no join materialized. **build** = the accumulate INSERTs that
materialize the full detail/summary output rows (q1–q4 total). Q3's summary
scope reads the maintained `crown_fact_ids` (distinct fact ids + fan-out count)
and weights its SUMs by the count, so it never assembles the fact join.

### DuckDB

| scenario | ivm maint / count / build | crown maint / count / build |
|---|---|---|
| insertion_only | 1.95 / 0.22 / 2.47 | 0.43 / 0.98 / 1.76 |
| sliding_window | 0.57 / 0.04 / 0.22 | 0.57 / 0.07 / 0.31 |
| preloaded_replacement_sliding | 3.54 / 0.45 / 5.81 | 0.73 / 2.43 / 4.83 |

### openGauss

| scenario | ivm maint / count / build | crown maint / count / build |
|---|---|---|
| insertion_only | 6.46 / 7.82 / 9.06 | 2.00 / 2.17 / **4.65** |
| sliding_window | 2.30 / 0.26 / 0.30 | 2.04 / 0.35 / 0.38 |
| preloaded_replacement_sliding | 10.98 / 6.32 / 9.81 | 4.12 / 4.17 / **10.26** |

Combined maintain+queries per step (openGauss): insertion **crown 6.65** vs
ivm 15.51 vs recompute 46.69; preloaded **crown 14.38** vs ivm 20.79 vs
recompute 111.35.

Reading the numbers:

- **Maintenance:** `crown` is markedly cheaper than `ivm` everywhere (it does
  no join work), even after adding `crown_fact_ids` upkeep.
- **Count queries:** `crown` aggregates partial counts, never assembling the
  join — well below `recompute`/`logical_views` on openGauss.
- **Build:** with Q3's scope reading `crown_fact_ids` (not `fact_t_cw`), crown
  no longer re-assembles the fact for the summary; its build dropped sharply on
  openGauss (Q3 alone 36→2 s at preloaded), so `crown` now wins the combined
  maintain+queries metric on both engines. `q1` still assembles the fact view
  at query time to emit the full detail rows — the remaining build cost.

Net: `crown` is cheapest on maintenance and on count/aggregate queries, and now
also wins the combined build+query total; the only residual cost is emitting the
full detail rows (q1), which any method must pay.
