# Random large balanced sample — 2026-08-28

Independent C++ paired timings on 40 new `gen-forest` instances: sizes 10,000
through 100,000, sparse and medium densities, uncorrelated and strongly
correlated coefficients, one deterministic seed per combination.

| n | median RaC/HFMA |
| --: | --: |
| 10,000 | 3.70 |
| 20,000 | 5.03 |
| 30,000 | 7.39 |
| 40,000 | 9.21 |
| 50,000 | 11.48 |
| 60,000 | 13.83 |
| 70,000 | 15.25 |
| 80,000 | 17.92 |
| 90,000 | 20.07 |
| 100,000 | 21.82 |

The campaign is deliberately a balanced large sample, not the full Cartesian
product. Raw timings are in `raw_random_large_balanced.csv`.
