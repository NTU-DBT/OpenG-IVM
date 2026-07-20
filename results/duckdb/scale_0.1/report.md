# Benchmark report — results/duckdb/scale_0.1

Timings in seconds. `maintain` = incremental maintenance per step (recompute/logical_views have none). `query qN` = the qN accumulate INSERT per step. Shared costs (staging, base INSERT/DELETE, ANALYZE, checkpoint fences) are reported separately, not attributed to any method.

## Correctness

- Per-step count + min/max agreement (q1-q4, all methods vs recompute): **all pass**
- Final multiset comparison of accumulated outputs (deterministic columns) and fact_t (ivm vs crown): **0 differing rows in all comparisons**


## insertion_only  (20 steps)

Shared costs: staging 89.5s, base_insert 79.4s, base_delete 0.0s, checkpoint 23.8s, analyze 0.0s. Method init (incl. indexes): logical_views 0.08s, ivm 0.07s, crown 0.12s.

| method | maintain/step | q1 | q2 | q3 | q4 | queries/step | maintain+queries/step |
|---|---|---|---|---|---|---|---|
| recompute | 0.000 | 1.101 | 0.219 | 0.689 | 0.018 | 2.026 | 2.026 |
| logical_views | 0.000 | 1.212 | 0.206 | 0.692 | 0.017 | 2.127 | 2.127 |
| ivm | 1.951 | 1.640 | 0.175 | 0.596 | 0.019 | 2.431 | 4.382 |
| crown | 0.311 | 1.333 | 0.196 | 0.658 | 0.020 | 2.207 | 2.518 |
- ivm maintain per step: min 0.306s, median 1.872s, max 4.569s
- crown maintain per step: min 0.194s, median 0.314s, max 0.390s

## sliding_window  (20 steps)

Shared costs: staging 167.0s, base_insert 79.8s, base_delete 6.7s, checkpoint 25.5s, analyze 0.0s. Method init (incl. indexes): logical_views 0.06s, ivm 0.06s, crown 0.11s.

| method | maintain/step | q1 | q2 | q3 | q4 | queries/step | maintain+queries/step |
|---|---|---|---|---|---|---|---|
| recompute | 0.000 | 0.168 | 0.090 | 0.107 | 0.011 | 0.376 | 0.376 |
| logical_views | 0.000 | 0.188 | 0.072 | 0.097 | 0.011 | 0.368 | 0.368 |
| ivm | 0.561 | 0.099 | 0.047 | 0.054 | 0.011 | 0.212 | 0.772 |
| crown | 0.494 | 0.184 | 0.060 | 0.066 | 0.011 | 0.321 | 0.816 |
- ivm maintain per step: min 0.301s, median 0.579s, max 0.616s
- crown maintain per step: min 0.194s, median 0.438s, max 0.676s

## preloaded_replacement_sliding  (20 steps)

Shared costs: staging 176.4s, base_insert 85.5s, base_delete 7.9s, checkpoint 29.9s, analyze 0.0s. Method init (incl. indexes): logical_views 0.05s, ivm 3.91s, crown 1.17s.

| method | maintain/step | q1 | q2 | q3 | q4 | queries/step | maintain+queries/step |
|---|---|---|---|---|---|---|---|
| recompute | 0.000 | 1.950 | 1.710 | 1.180 | 0.045 | 4.885 | 4.885 |
| logical_views | 0.000 | 2.330 | 1.661 | 1.093 | 0.041 | 5.124 | 5.124 |
| ivm | 3.470 | 2.865 | 1.830 | 1.044 | 0.044 | 5.783 | 9.254 |
| crown | 0.535 | 2.577 | 1.838 | 1.088 | 0.041 | 5.544 | 6.079 |
- ivm maintain per step: min 2.582s, median 3.414s, max 4.774s
- crown maintain per step: min 0.510s, median 0.535s, max 0.578s
