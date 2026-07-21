# Benchmark report — results/duckdb/scale_0.1

Timings in seconds. `maintain` = incremental maintenance per step (recompute/logical_views have none). `query qN` = the qN accumulate INSERT per step. Shared costs (staging, base INSERT/DELETE, ANALYZE, checkpoint fences) are reported separately, not attributed to any method.

## Correctness

- Per-step count + min/max agreement (q1-q4, all methods vs recompute): **all pass**
- Final multiset comparison of accumulated outputs (deterministic columns) and fact_t (ivm vs crown): **0 differing rows in all comparisons**


## insertion_only  (20 steps)

Shared costs: staging 89.5s, base_insert 78.9s, base_delete 0.0s, checkpoint 24.6s, analyze 0.0s. Method init (incl. indexes): logical_views 0.06s, ivm 0.06s, crown 0.12s.

Accumulate-INSERT cost (builds the detail/summary output tables):

| method | maintain/step | q1 | q2 | q3 | q4 | queries/step | maintain+queries/step |
|---|---|---|---|---|---|---|---|
| recompute | 0.000 | 1.116 | 0.198 | 0.707 | 0.022 | 2.042 | 2.042 |
| logical_views | 0.000 | 1.220 | 0.204 | 0.681 | 0.021 | 2.125 | 2.125 |
| ivm | 1.976 | 1.601 | 0.175 | 0.628 | 0.020 | 2.424 | 4.400 |
| crown | 0.311 | 1.331 | 0.189 | 0.650 | 0.020 | 2.190 | 2.501 |

Count-form cost (COUNT of the current result; crown aggregates partial counts instead of materializing the join):

| method | cf_q1 | cf_q2 | cf_q3 | cf_q4 | count-form/step |
|---|---|---|---|---|---|
| recompute | 0.259 | 0.197 | 0.617 | 0.008 | 1.081 |
| logical_views | 0.130 | 0.091 | 0.118 | 0.009 | 0.347 |
| ivm | 0.114 | 0.051 | 0.048 | 0.008 | 0.222 |
| crown | 0.936 | 0.047 | 0.025 | 0.010 | 1.018 |

- ivm maintain per step: min 0.327s, median 1.789s, max 4.883s
- crown maintain per step: min 0.223s, median 0.324s, max 0.380s

## sliding_window  (20 steps)

Shared costs: staging 167.9s, base_insert 80.1s, base_delete 6.6s, checkpoint 25.9s, analyze 0.0s. Method init (incl. indexes): logical_views 0.06s, ivm 0.06s, crown 0.12s.

Accumulate-INSERT cost (builds the detail/summary output tables):

| method | maintain/step | q1 | q2 | q3 | q4 | queries/step | maintain+queries/step |
|---|---|---|---|---|---|---|---|
| recompute | 0.000 | 0.160 | 0.091 | 0.103 | 0.014 | 0.368 | 0.368 |
| logical_views | 0.000 | 0.184 | 0.076 | 0.095 | 0.013 | 0.367 | 0.367 |
| ivm | 0.574 | 0.098 | 0.047 | 0.054 | 0.011 | 0.210 | 0.783 |
| crown | 0.505 | 0.186 | 0.059 | 0.073 | 0.012 | 0.330 | 0.835 |

Count-form cost (COUNT of the current result; crown aggregates partial counts instead of materializing the join):

| method | cf_q1 | cf_q2 | cf_q3 | cf_q4 | count-form/step |
|---|---|---|---|---|---|
| recompute | 0.129 | 0.071 | 0.069 | 0.004 | 0.272 |
| logical_views | 0.065 | 0.046 | 0.049 | 0.004 | 0.164 |
| ivm | 0.017 | 0.012 | 0.006 | 0.004 | 0.038 |
| crown | 0.036 | 0.018 | 0.008 | 0.004 | 0.065 |

- ivm maintain per step: min 0.325s, median 0.595s, max 0.641s
- crown maintain per step: min 0.193s, median 0.455s, max 0.766s

## preloaded_replacement_sliding  (20 steps)

Shared costs: staging 177.5s, base_insert 86.5s, base_delete 8.0s, checkpoint 30.6s, analyze 0.0s. Method init (incl. indexes): logical_views 0.06s, ivm 3.97s, crown 1.11s.

Accumulate-INSERT cost (builds the detail/summary output tables):

| method | maintain/step | q1 | q2 | q3 | q4 | queries/step | maintain+queries/step |
|---|---|---|---|---|---|---|---|
| recompute | 0.000 | 1.952 | 1.681 | 1.217 | 0.050 | 4.901 | 4.901 |
| logical_views | 0.000 | 2.336 | 1.687 | 1.110 | 0.042 | 5.175 | 5.175 |
| ivm | 3.489 | 2.858 | 1.862 | 0.992 | 0.043 | 5.755 | 9.245 |
| crown | 0.543 | 2.595 | 1.843 | 1.101 | 0.042 | 5.582 | 6.125 |

Count-form cost (COUNT of the current result; crown aggregates partial counts instead of materializing the join):

| method | cf_q1 | cf_q2 | cf_q3 | cf_q4 | count-form/step |
|---|---|---|---|---|---|
| recompute | 0.256 | 0.466 | 1.088 | 0.029 | 1.839 |
| logical_views | 0.212 | 0.157 | 0.216 | 0.025 | 0.609 |
| ivm | 0.195 | 0.118 | 0.107 | 0.024 | 0.444 |
| crown | 2.242 | 0.105 | 0.070 | 0.029 | 2.446 |

- ivm maintain per step: min 2.656s, median 3.464s, max 4.649s
- crown maintain per step: min 0.499s, median 0.540s, max 0.587s
