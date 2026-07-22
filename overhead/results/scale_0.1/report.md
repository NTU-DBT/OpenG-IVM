# Compute-overhead experiment — DuckDB, scale 0.1, threads 4

Per-method computing overhead in a dedicated in-memory DuckDB process. **maint CPU** = CPU seconds in incremental maintenance (0 for recompute / logical_views — they do no maintenance); **query CPU** = CPU in the q1–q4 build + count forms; **total CPU** = whole process (incl. shared base updates). **state rows** = rows held in the method's persistent tables — the clean persistent-state footprint (crown's rows are also far narrower: (id,cdc,cnt)/counts/flags vs ivm's 35-column joined rows). **state RSS** = process resident memory after the run; it is dominated by the in-memory base data plus DuckDB's transient query high-water (which does not shrink), so it is a noisy proxy for state size — prefer state rows. `base_only` = base updates only (shared baseline).


## insertion_only

| method | maint CPU s | query CPU s | total CPU s | state RSS MB | ΔRSS vs base | state rows |
|---|---|---|---|---|---|---|
| base_only | 0.00 | 0.00 | 184.33 | 6492.0 | +0.0 | 0 |
| recompute | 0.00 | 137.77 | 327.47 | 8262.8 | +1770.8 | 0 |
| logical_views | 0.00 | 100.88 | 289.04 | 8181.8 | +1689.8 | 0 |
| ivm | 39.95 | 83.84 | 312.81 | 8532.5 | +2040.5 | 2456129 |
| crown | 11.79 | 152.84 | 352.24 | 7416.3 | +924.3 | 1112888 |

## sliding_window

| method | maint CPU s | query CPU s | total CPU s | state RSS MB | ΔRSS vs base | state rows |
|---|---|---|---|---|---|---|
| base_only | 0.00 | 0.00 | 323.51 | 6541.1 | +0.0 | 0 |
| recompute | 0.00 | 29.23 | 352.33 | 6744.4 | +203.3 | 0 |
| logical_views | 0.00 | 24.17 | 347.12 | 6687.2 | +146.1 | 0 |
| ivm | 14.39 | 7.19 | 345.08 | 6632.5 | +91.4 | 121447 |
| crown | 14.79 | 17.50 | 355.65 | 6644.7 | +103.6 | 129143 |

## preloaded_replacement_sliding

| method | maint CPU s | query CPU s | total CPU s | state RSS MB | ΔRSS vs base | state rows |
|---|---|---|---|---|---|---|
| base_only | 0.00 | 0.00 | 503.97 | 11769.0 | +0.0 | 0 |
| recompute | 0.00 | 421.82 | 936.12 | 14054.0 | +2285.0 | 0 |
| logical_views | 0.00 | 285.76 | 800.96 | 13818.7 | +2049.7 | 0 |
| ivm | 66.96 | 267.31 | 859.52 | 14570.4 | +2801.4 | 2451823 |
| crown | 19.84 | 481.38 | 1025.04 | 15146.2 | +3377.2 | 1112850 |
