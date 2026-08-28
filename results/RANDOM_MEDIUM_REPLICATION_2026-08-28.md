# Random medium replication — 2026-08-28

The independent `gen-forest` test bed contains 2,400 new instances:

- sizes 100, 200, ..., 1,000;
- densities 0.3, 0.6, 0.9 and 1.0;
- six profit-weight families;
- ten deterministic seeds per combination.

HFMA and RaC were measured in the same Release C++ process, once per instance.
The raw file has 4,800 algorithm rows.

| aggregation | median RaC/HFMA |
| --- | ---: |
| all instances | 2.51 |
| sparse (0.3) | 2.75 |
| medium (0.6) | 3.05 |
| dense (0.9) | 2.11 |
| tree (1.0) | 1.73 |

The 10th and 90th percentiles of the per-instance ratio are 1.34 and 3.35.
Thus HFMA is faster in the complete random medium replication, consistently with
the conditional conclusion in the paper. This record is a new experiment; it
does not reuse old raw data.
