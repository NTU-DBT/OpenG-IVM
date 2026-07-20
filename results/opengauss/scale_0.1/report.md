# Benchmark report — results/opengauss/scale_0.1

Timings in seconds. `maintain` = incremental maintenance per step (recompute/logical_views have none). `query qN` = the qN accumulate INSERT per step. Shared costs (staging, base INSERT/DELETE, ANALYZE, checkpoint fences) are reported separately, not attributed to any method.

## Correctness

- Per-step count + min/max agreement (q1-q4, all methods vs recompute): **all pass**
- Final multiset comparison of accumulated outputs (deterministic columns) and fact_t (ivm vs crown): **0 differing rows in all comparisons**


## insertion_only  (20 steps)

Shared costs: staging 44.6s, base_insert 10.6s, base_delete 0.0s, analyze 172.2s. Method init (incl. indexes): logical_views 0.12s, ivm 0.35s, crown 0.33s.

| method | maintain/step | q1 | q2 | q3 | q4 | queries/step | maintain+queries/step |
|---|---|---|---|---|---|---|---|
| recompute | 0.000 | 12.497 | 9.916 | 24.083 | 0.116 | 46.612 | 46.612 |
| logical_views | 0.000 | 3.443 | 1.348 | 17.068 | 0.117 | 21.976 | 21.976 |
| ivm | 6.538 | 1.481 | 0.492 | 6.939 | 0.115 | 9.027 | 15.565 |
| crown | 1.144 | 2.389 | 0.681 | 15.743 | 0.119 | 18.932 | 20.077 |
- ivm maintain per step: min 1.388s, median 5.976s, max 13.604s
- crown maintain per step: min 0.703s, median 1.191s, max 1.372s

## sliding_window  (20 steps)

Shared costs: staging 83.7s, base_insert 11.3s, base_delete 10.5s, analyze 231.3s. Method init (incl. indexes): logical_views 0.11s, ivm 0.35s, crown 0.30s.

| method | maintain/step | q1 | q2 | q3 | q4 | queries/step | maintain+queries/step |
|---|---|---|---|---|---|---|---|
| recompute | 0.000 | 0.366 | 0.330 | 0.326 | 0.059 | 1.080 | 1.080 |
| logical_views | 0.000 | 0.412 | 0.272 | 0.384 | 0.061 | 1.129 | 1.129 |
| ivm | 2.372 | 0.093 | 0.066 | 0.077 | 0.061 | 0.297 | 2.669 |
| crown | 1.653 | 0.151 | 0.106 | 0.129 | 0.060 | 0.445 | 2.099 |
- ivm maintain per step: min 1.419s, median 2.374s, max 2.763s
- crown maintain per step: min 0.692s, median 1.682s, max 1.990s

## preloaded_replacement_sliding  (20 steps)

Shared costs: staging 86.4s, base_insert 10.2s, base_delete 13.8s, analyze 173.8s. Method init (incl. indexes): logical_views 0.17s, ivm 11.94s, crown 4.11s.

| method | maintain/step | q1 | q2 | q3 | q4 | queries/step | maintain+queries/step |
|---|---|---|---|---|---|---|---|
| recompute | 0.000 | 27.064 | 28.165 | 56.817 | 0.156 | 112.203 | 112.203 |
| logical_views | 0.000 | 6.981 | 4.021 | 41.874 | 0.165 | 53.040 | 53.040 |
| ivm | 11.087 | 3.394 | 2.324 | 3.756 | 0.160 | 9.635 | 20.721 |
| crown | 2.390 | 4.804 | 3.086 | 36.638 | 0.165 | 44.693 | 47.083 |
- ivm maintain per step: min 7.346s, median 10.281s, max 17.517s
- crown maintain per step: min 2.153s, median 2.388s, max 2.597s
