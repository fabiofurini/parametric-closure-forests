# Structured pilot — 2026-08-28

Release build, Intel i7-12700. Each cell is the median of 15 in-process C++
measurements: 3 deterministic instances times 5 repetitions.  Times are in ms.
The raw CSV files are retained beside this report.

## Mixed star: RaC should win

| n | RaC | HFMA | HFMA/RaC |
| --: | --: | --: | --: |
| 100 | 0.330 | 0.924 | 2.80 |
| 200 | 0.692 | 3.999 | 5.78 |
| 500 | 1.851 | 27.867 | 15.05 |
| 1000 | 3.653 | 126.041 | 34.51 |
| 2000 | 7.340 | 669.213 | 91.18 |

## Mixed path: HFMA should win

| n | HFMA | RaC | RaC/HFMA |
| --: | --: | --: | --: |
| 100 | 0.089 | 0.649 | 7.78 |
| 200 | 0.121 | 0.905 | 7.96 |
| 500 | 0.470 | 3.144 | 7.92 |
| 1000 | 0.587 | 5.049 | 8.58 |
| 2000 | 1.217 | 10.660 | 8.83 |

## Mixed binary: HFMA should win

| n | HFMA | RaC | RaC/HFMA |
| --: | --: | --: | --: |
| 100 | 0.165 | 0.460 | 2.43 |
| 200 | 0.396 | 0.942 | 2.29 |
| 500 | 0.775 | 1.576 | 2.07 |
| 1000 | 1.636 | 3.313 | 2.00 |
| 2000 | 3.477 | 6.634 | 1.92 |

Every one of the 75 paired measurements for each of path and binary had
`RaC/HFMA > 1`; the smallest observed ratios were 3.45 and 1.70 respectively.
This is a pilot validation only: it uses the newly generated instances and does
not replace the preregistered complete random campaign.
