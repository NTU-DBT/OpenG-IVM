# Benchmark report — results/duckdb/scale_0.1

Timings in seconds. `maintain` = incremental maintenance per step (recompute/logical_views have none). `query qN` = the qN accumulate INSERT per step. Shared costs (staging, base INSERT/DELETE, ANALYZE, checkpoint fences) are reported separately, not attributed to any method.

## Correctness

- Per-step count + min/max agreement (q1-q4, all methods vs recompute): **all pass**
- Final multiset comparison of accumulated outputs (deterministic columns) and fact_t (ivm vs crown): **0 differing rows in all comparisons**


## insertion_only  (20 steps)

Shared costs: staging 91.0s, base_insert 78.8s, base_delete 0.0s, checkpoint 24.7s, analyze 0.0s. Method init (incl. indexes): logical_views 0.08s, ivm 0.07s, crown 0.13s.

Accumulate-INSERT cost (builds the detail/summary output tables):

| method | maintain/step | q1 | q2 | q3 | q4 | queries/step | maintain+queries/step |
|---|---|---|---|---|---|---|---|
| recompute | 0.000 | 1.107 | 0.197 | 0.703 | 0.023 | 2.030 | 2.030 |
| logical_views | 0.000 | 1.225 | 0.202 | 0.689 | 0.021 | 2.137 | 2.137 |
| ivm | 1.949 | 1.660 | 0.183 | 0.607 | 0.019 | 2.467 | 4.416 |
| crown | 0.433 | 1.346 | 0.184 | 0.209 | 0.017 | 1.756 | 2.189 |

Count-form cost (COUNT of the current result; crown aggregates partial counts instead of materializing the join):

| method | cf_q1 | cf_q2 | cf_q3 | cf_q4 | count-form/step |
|---|---|---|---|---|---|
| recompute | 0.256 | 0.197 | 0.628 | 0.009 | 1.090 |
| logical_views | 0.132 | 0.093 | 0.116 | 0.007 | 0.348 |
| ivm | 0.110 | 0.052 | 0.049 | 0.008 | 0.220 |
| crown | 0.904 | 0.045 | 0.019 | 0.008 | 0.976 |

- ivm maintain per step: min 0.313s, median 1.868s, max 4.529s
- crown maintain per step: min 0.261s, median 0.420s, max 0.557s

## sliding_window  (20 steps)

Shared costs: staging 169.4s, base_insert 80.3s, base_delete 6.8s, checkpoint 26.1s, analyze 0.0s. Method init (incl. indexes): logical_views 0.05s, ivm 0.06s, crown 0.14s.

Accumulate-INSERT cost (builds the detail/summary output tables):

| method | maintain/step | q1 | q2 | q3 | q4 | queries/step | maintain+queries/step |
|---|---|---|---|---|---|---|---|
| recompute | 0.000 | 0.167 | 0.094 | 0.116 | 0.014 | 0.391 | 0.391 |
| logical_views | 0.000 | 0.183 | 0.082 | 0.104 | 0.012 | 0.382 | 0.382 |
| ivm | 0.568 | 0.105 | 0.049 | 0.055 | 0.011 | 0.219 | 0.787 |
| crown | 0.573 | 0.183 | 0.061 | 0.053 | 0.011 | 0.309 | 0.882 |

Count-form cost (COUNT of the current result; crown aggregates partial counts instead of materializing the join):

| method | cf_q1 | cf_q2 | cf_q3 | cf_q4 | count-form/step |
|---|---|---|---|---|---|
| recompute | 0.132 | 0.071 | 0.071 | 0.004 | 0.278 |
| logical_views | 0.065 | 0.049 | 0.048 | 0.004 | 0.166 |
| ivm | 0.018 | 0.013 | 0.006 | 0.004 | 0.041 |
| crown | 0.037 | 0.020 | 0.006 | 0.004 | 0.067 |

- ivm maintain per step: min 0.295s, median 0.592s, max 0.627s
- crown maintain per step: min 0.273s, median 0.539s, max 0.810s

## preloaded_replacement_sliding  (20 steps)

Shared costs: staging 181.7s, base_insert 86.0s, base_delete 8.1s, checkpoint 30.9s, analyze 0.0s. Method init (incl. indexes): logical_views 0.05s, ivm 3.87s, crown 1.15s.

Accumulate-INSERT cost (builds the detail/summary output tables):

| method | maintain/step | q1 | q2 | q3 | q4 | queries/step | maintain+queries/step |
|---|---|---|---|---|---|---|---|
| recompute | 0.000 | 1.989 | 1.681 | 1.204 | 0.055 | 4.929 | 4.929 |
| logical_views | 0.000 | 2.371 | 1.693 | 1.120 | 0.047 | 5.232 | 5.232 |
| ivm | 3.538 | 2.894 | 1.847 | 1.027 | 0.042 | 5.810 | 9.347 |
| crown | 0.732 | 2.682 | 1.705 | 0.395 | 0.044 | 4.825 | 5.557 |

Count-form cost (COUNT of the current result; crown aggregates partial counts instead of materializing the join):

| method | cf_q1 | cf_q2 | cf_q3 | cf_q4 | count-form/step |
|---|---|---|---|---|---|
| recompute | 0.256 | 0.467 | 1.105 | 0.029 | 1.857 |
| logical_views | 0.222 | 0.159 | 0.218 | 0.026 | 0.625 |
| ivm | 0.205 | 0.111 | 0.110 | 0.026 | 0.452 |
| crown | 2.259 | 0.100 | 0.045 | 0.028 | 2.431 |

- ivm maintain per step: min 2.712s, median 3.385s, max 4.800s
- crown maintain per step: min 0.680s, median 0.730s, max 0.810s
