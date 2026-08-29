# HFMA versus DHFMA — 2026-08-28

## Scope and protocol

This is a paired implementation comparison.  Both algorithms receive the same
`.pcf` instances and use exact rational comparisons.  The reported quantity is
the median, over instances in a group, of

\[
\frac{\text{median DHFMA elapsed time per instance}}
     {\text{median HFMA elapsed time per instance}}.
\]

A value below one favours DHFMA.  Timings are wall-clock nanoseconds measured
by `pcf_benchmark` in the Release build on `canarino` (Intel Core i7-12700,
GCC 11.4).  The algorithms were run in the fixed order `hfma,dhfma`; this is a
useful implementation comparison, but not yet a final paper-ready timing
campaign with randomized order and process isolation.

The code names have the following meaning:

| Algorithm | Direction | Domain |
|---|---|---|
| HFMA | primal heap-based FMA | generic directed forests |
| DHFMA | dual heap-based FMA | generic directed forests |
| HOMA | specialized dual heap method | out-forests only |

## Random medium campaign

Raw data: `raw_hfma_dhfma_random_medium_2026-08-28.csv`.

- 2,400 independently generated mixed-orientation forests;
- sizes `n=100,200,...,1000`;
- densities `rho=0.3,0.6,0.9,1.0`;
- six coefficient families and ten seeds per cell;
- three repetitions for each algorithm and instance.

Overall median `DHFMA/HFMA`: **1.048**.  DHFMA is therefore about 4.8% slower
in the median on this medium campaign, with no material separation by
coefficient family.

| coefficient family | instances | median DHFMA/HFMA |
|---|---:|---:|
| strongly-corr | 400 | 1.042 |
| strongly-corr-neg | 400 | 1.024 |
| uncorr | 400 | 1.064 |
| uncorr-neg | 400 | 1.050 |
| weakly-corr | 400 | 1.069 |
| weakly-corr-neg | 400 | 1.031 |

| density | instances | median DHFMA/HFMA |
|---|---:|---:|
| 0.3 | 600 | 1.178 |
| 0.6 | 600 | 1.062 |
| 0.9 | 600 | 0.995 |
| 1.0 | 600 | 0.959 |

The relative behaviour changes with density: HFMA is faster on sparse random
forests, while DHFMA is slightly faster at the two densest settings.  Across
the ten sizes, the medians stay between 1.011 and 1.079, so there is no size
trend in this range.

## Structured topologies

Raw data: `raw_hfma_dhfma_path_2026-08-28.csv`,
`raw_hfma_dhfma_binary_2026-08-28.csv`, and
`raw_hfma_dhfma_star_2026-08-28.csv`.

Each topology uses `n=100,200,500,1000,2000`, three coefficient seeds, and
five repetitions per algorithm/instance.

| topology | median DHFMA/HFMA |
|---|---:|
| path | 1.056 |
| balanced binary tree | 1.040 |
| mixed-orientation star | 1.017 |

HFMA is modestly faster on every structured family in this pilot; the gap is
smallest on stars.

## Random large campaign

Raw data: `raw_hfma_dhfma_random_large_2026-08-28.csv`.

- 40 mixed-orientation forests;
- sizes `n=10,000,20,000,...,100,000`;
- densities `rho=0.3,0.6`;
- `uncorr` and `strongly-corr` coefficient families;
- one deterministic generated instance per cell and three timing repetitions.

Overall median `DHFMA/HFMA`: **1.027**.  Median ratios by size are stable:

| n | median DHFMA/HFMA |
|---:|---:|
| 10,000 | 1.051 |
| 20,000 | 1.032 |
| 30,000 | 1.044 |
| 40,000 | 1.030 |
| 50,000 | 1.020 |
| 60,000 | 1.020 |
| 70,000 | 1.029 |
| 80,000 | 1.041 |
| 90,000 | 1.014 |
| 100,000 | 1.036 |

By family, the medians are 1.007 for `strongly-corr` and 1.061 for `uncorr`.
By density, they are 1.025 at `rho=0.3` and 1.030 at `rho=0.6`.

## Current conclusion

The generic dual heap implementation is operationally competitive with HFMA:
on these campaigns its median overhead is about 3–5%, and it can be slightly
faster on dense medium random forests.  This justifies retaining both generic
directions in the computational core.  A final experimental claim requires
the preregistered full campaign with shuffled algorithm order, more seeds at
large size, and a memory measurement.
