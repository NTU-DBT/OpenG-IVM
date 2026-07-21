# Benchmark report — results/opengauss/scale_0.1

Timings in seconds. `maintain` = incremental maintenance per step (recompute/logical_views have none). `query qN` = the qN accumulate INSERT per step. Shared costs (staging, base INSERT/DELETE, ANALYZE, checkpoint fences) are reported separately, not attributed to any method.

## Correctness

- Per-step count + min/max agreement (q1-q4, all methods vs recompute): **all pass**
- Final multiset comparison of accumulated outputs (deterministic columns) and fact_t (ivm vs crown): **0 differing rows in all comparisons**


## insertion_only  (20 steps)

Shared costs: staging 44.5s, base_insert 10.7s, base_delete 0.0s, analyze 183.6s. Method init (incl. indexes): logical_views 0.11s, ivm 0.35s, crown 0.29s.

Accumulate-INSERT cost (builds the detail/summary output tables):

| method | maintain/step | q1 | q2 | q3 | q4 | queries/step | maintain+queries/step |
|---|---|---|---|---|---|---|---|
| recompute | 0.000 | 12.517 | 9.897 | 24.078 | 0.120 | 46.613 | 46.613 |
| logical_views | 0.000 | 3.450 | 1.349 | 17.028 | 0.121 | 21.948 | 21.948 |
| ivm | 6.429 | 1.514 | 0.499 | 9.423 | 0.119 | 11.555 | 17.985 |
| crown | 1.152 | 2.378 | 0.709 | 15.829 | 0.116 | 19.032 | 20.183 |

Count-form cost (COUNT of the current result; crown aggregates partial counts instead of materializing the join):

| method | cf_q1 | cf_q2 | cf_q3 | cf_q4 | count-form/step |
|---|---|---|---|---|---|
| recompute | 11.589 | 9.898 | 24.026 | 0.110 | 45.623 |
| logical_views | 2.656 | 1.141 | 16.901 | 0.111 | 20.810 |
| ivm | 0.482 | 0.331 | 9.447 | 0.112 | 10.371 |
| crown | 0.359 | 0.325 | 0.255 | 0.111 | 1.050 |

- ivm maintain per step: min 1.345s, median 5.242s, max 14.708s
- crown maintain per step: min 0.704s, median 1.197s, max 1.424s

## sliding_window  (20 steps)

Shared costs: staging 86.1s, base_insert 11.2s, base_delete 10.7s, analyze 246.2s. Method init (incl. indexes): logical_views 0.12s, ivm 0.35s, crown 0.31s.

Accumulate-INSERT cost (builds the detail/summary output tables):

| method | maintain/step | q1 | q2 | q3 | q4 | queries/step | maintain+queries/step |
|---|---|---|---|---|---|---|---|
| recompute | 0.000 | 0.373 | 0.334 | 0.326 | 0.060 | 1.092 | 1.092 |
| logical_views | 0.000 | 0.413 | 0.268 | 0.386 | 0.058 | 1.125 | 1.125 |
| ivm | 2.464 | 0.094 | 0.065 | 0.077 | 0.059 | 0.295 | 2.759 |
| crown | 1.695 | 0.154 | 0.102 | 0.128 | 0.059 | 0.443 | 2.138 |

Count-form cost (COUNT of the current result; crown aggregates partial counts instead of materializing the join):

| method | cf_q1 | cf_q2 | cf_q3 | cf_q4 | count-form/step |
|---|---|---|---|---|---|
| recompute | 0.340 | 0.322 | 0.325 | 0.055 | 1.042 |
| logical_views | 0.383 | 0.260 | 0.382 | 0.055 | 1.080 |
| ivm | 0.067 | 0.059 | 0.070 | 0.056 | 0.252 |
| crown | 0.153 | 0.073 | 0.061 | 0.055 | 0.342 |

- ivm maintain per step: min 1.378s, median 2.403s, max 3.269s
- crown maintain per step: min 0.686s, median 1.718s, max 2.125s

## preloaded_replacement_sliding  (20 steps)

Shared costs: staging 84.2s, base_insert 10.2s, base_delete 14.0s, analyze 177.0s. Method init (incl. indexes): logical_views 0.18s, ivm 12.02s, crown 4.50s.

Accumulate-INSERT cost (builds the detail/summary output tables):

| method | maintain/step | q1 | q2 | q3 | q4 | queries/step | maintain+queries/step |
|---|---|---|---|---|---|---|---|
| recompute | 0.000 | 26.826 | 27.738 | 56.196 | 0.160 | 110.920 | 110.920 |
| logical_views | 0.000 | 6.919 | 4.031 | 41.578 | 0.170 | 52.699 | 52.699 |
| ivm | 10.613 | 3.390 | 2.318 | 3.947 | 0.153 | 9.808 | 20.421 |
| crown | 2.338 | 4.817 | 3.248 | 36.235 | 0.170 | 44.470 | 46.808 |

Count-form cost (COUNT of the current result; crown aggregates partial counts instead of materializing the join):

| method | cf_q1 | cf_q2 | cf_q3 | cf_q4 | count-form/step |
|---|---|---|---|---|---|
| recompute | 25.095 | 24.650 | 55.910 | 0.144 | 105.798 |
| logical_views | 4.916 | 3.064 | 41.354 | 0.156 | 49.490 |
| ivm | 0.808 | 1.492 | 3.941 | 0.152 | 6.393 |
| crown | 0.626 | 1.388 | 0.702 | 0.157 | 2.874 |

- ivm maintain per step: min 7.430s, median 10.075s, max 16.851s
- crown maintain per step: min 2.142s, median 2.318s, max 2.569s
