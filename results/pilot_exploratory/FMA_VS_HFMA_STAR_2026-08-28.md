# FMA versus HFMA on mixed-orientation stars — 2026-08-28

Raw data: `raw_fma_hfma_star_2026-08-28.csv`.

Protocol: the same mixed-orientation star instances used in the structured
pilot; three coefficient seeds at each size and five repetitions for each
algorithm/instance.  Entries below are medians over the three per-instance
timing medians, measured by `pcf_benchmark` in the Release build.

| n | instances | FMA (ms) | HFMA (ms) | FMA/HFMA |
|---:|---:|---:|---:|---:|
| 100 | 3 | 0.363 | 1.004 | 0.36 |
| 200 | 3 | 1.201 | 3.919 | 0.31 |
| 500 | 3 | 7.055 | 26.805 | 0.26 |
| 1,000 | 3 | 28.714 | 120.702 | 0.24 |
| 2,000 | 3 | 120.677 | 593.223 | 0.21 |

The median FMA/HFMA ratio over the fifteen instances is **0.26**.  Hence FMA
is faster on this family, by about 2.8x at `n=100` and 4.9x at `n=2,000`.
This is consistent with the star being unfavourable to HFMA's lazy-heap update
mechanism: many candidate ratios are invalidated after each central update.
