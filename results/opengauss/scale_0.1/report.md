# Benchmark report — results/opengauss/scale_0.1

Timings in seconds. `maintain` = incremental maintenance per step (recompute/logical_views have none). `query qN` = the qN accumulate INSERT per step. Shared costs (staging, base INSERT/DELETE, ANALYZE, checkpoint fences) are reported separately, not attributed to any method.

## Correctness

- Per-step count + min/max agreement (q1-q4, all methods vs recompute): **all pass**
- Final multiset comparison of accumulated outputs (deterministic columns) and fact_t (ivm vs crown): **0 differing rows in all comparisons**


## insertion_only  (20 steps)

Shared costs: staging 44.7s, base_insert 10.6s, base_delete 0.0s, analyze 171.5s. Method init (incl. indexes): logical_views 0.14s, ivm 0.42s, crown 0.38s.

Accumulate-INSERT cost (builds the detail/summary output tables):

| method | maintain/step | q1 | q2 | q3 | q4 | queries/step | maintain+queries/step |
|---|---|---|---|---|---|---|---|
| recompute | 0.000 | 12.485 | 9.933 | 24.156 | 0.118 | 46.692 | 46.692 |
| logical_views | 0.000 | 3.448 | 1.338 | 17.079 | 0.120 | 21.985 | 21.985 |
| ivm | 6.457 | 1.500 | 0.482 | 6.957 | 0.116 | 9.056 | 15.513 |
| crown | 1.995 | 2.331 | 0.684 | 1.524 | 0.115 | 4.653 | 6.648 |

Count-form cost (COUNT of the current result; crown aggregates partial counts instead of materializing the join):

| method | cf_q1 | cf_q2 | cf_q3 | cf_q4 | count-form/step |
|---|---|---|---|---|---|
| recompute | 11.623 | 9.914 | 24.084 | 0.109 | 45.730 |
| logical_views | 2.642 | 1.149 | 16.954 | 0.111 | 20.856 |
| ivm | 0.480 | 0.325 | 6.909 | 0.110 | 7.824 |
| crown | 0.357 | 0.330 | 1.377 | 0.110 | 2.174 |

- ivm maintain per step: min 1.360s, median 5.924s, max 14.090s
- crown maintain per step: min 0.965s, median 1.973s, max 3.177s

## sliding_window  (20 steps)

Shared costs: staging 79.6s, base_insert 10.6s, base_delete 10.1s, analyze 272.8s. Method init (incl. indexes): logical_views 0.12s, ivm 0.34s, crown 0.36s.

Accumulate-INSERT cost (builds the detail/summary output tables):

| method | maintain/step | q1 | q2 | q3 | q4 | queries/step | maintain+queries/step |
|---|---|---|---|---|---|---|---|
| recompute | 0.000 | 0.367 | 0.330 | 0.328 | 0.063 | 1.088 | 1.088 |
| logical_views | 0.000 | 0.412 | 0.270 | 0.387 | 0.060 | 1.129 | 1.129 |
| ivm | 2.303 | 0.095 | 0.066 | 0.077 | 0.061 | 0.299 | 2.602 |
| crown | 2.037 | 0.154 | 0.103 | 0.068 | 0.060 | 0.385 | 2.422 |

Count-form cost (COUNT of the current result; crown aggregates partial counts instead of materializing the join):

| method | cf_q1 | cf_q2 | cf_q3 | cf_q4 | count-form/step |
|---|---|---|---|---|---|
| recompute | 0.338 | 0.319 | 0.328 | 0.057 | 1.042 |
| logical_views | 0.383 | 0.259 | 0.382 | 0.055 | 1.078 |
| ivm | 0.068 | 0.061 | 0.073 | 0.057 | 0.259 |
| crown | 0.151 | 0.074 | 0.065 | 0.056 | 0.345 |

- ivm maintain per step: min 1.408s, median 2.383s, max 2.474s
- crown maintain per step: min 0.951s, median 2.161s, max 2.274s

## preloaded_replacement_sliding  (20 steps)

Shared costs: staging 83.4s, base_insert 10.2s, base_delete 13.3s, analyze 207.8s. Method init (incl. indexes): logical_views 0.17s, ivm 12.59s, crown 4.27s.

Accumulate-INSERT cost (builds the detail/summary output tables):

| method | maintain/step | q1 | q2 | q3 | q4 | queries/step | maintain+queries/step |
|---|---|---|---|---|---|---|---|
| recompute | 0.000 | 27.003 | 27.809 | 56.381 | 0.157 | 111.350 | 111.350 |
| logical_views | 0.000 | 6.921 | 4.062 | 41.744 | 0.170 | 52.897 | 52.897 |
| ivm | 10.982 | 3.370 | 2.383 | 3.900 | 0.154 | 9.806 | 20.788 |
| crown | 4.122 | 4.872 | 3.020 | 2.209 | 0.160 | 10.261 | 14.383 |

Count-form cost (COUNT of the current result; crown aggregates partial counts instead of materializing the join):

| method | cf_q1 | cf_q2 | cf_q3 | cf_q4 | count-form/step |
|---|---|---|---|---|---|
| recompute | 25.218 | 24.750 | 56.056 | 0.143 | 106.167 |
| logical_views | 4.931 | 3.050 | 41.573 | 0.156 | 49.710 |
| ivm | 0.813 | 1.517 | 3.839 | 0.151 | 6.320 |
| crown | 0.621 | 1.394 | 1.996 | 0.158 | 4.169 |

- ivm maintain per step: min 7.243s, median 10.590s, max 16.226s
- crown maintain per step: min 3.875s, median 4.135s, max 4.431s
