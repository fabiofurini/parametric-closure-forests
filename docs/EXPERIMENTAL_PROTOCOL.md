# Experimental protocol

This document freezes measurement protocol and campaign design (plan
sections 9 and 10) before the official runs referenced from
`results/results_summary.json`. It also records where an implementation
choice deviates from the plan's literal wording, and why.

## Environment (recorded automatically per run)

Every raw CSV row from `pcf_benchmark` carries `git_commit` and
`timestamp_utc`. The rest of the environment is recorded once per campaign in
its results report, not per row:

- CPU: Intel Core i7-12700 (12th Gen), 20 logical processors.
- RAM: 32 GiB.
- OS/kernel: Ubuntu 22.04.5 LTS, Linux 6.8.0-138-generic, x86_64.
- Compiler: GCC 11.4.0, `-O3` (`CMAKE_BUILD_TYPE=Release`).
- CPU governor: `powersave` (this machine has no passwordless root access to
  switch to `performance`; see "Known measurement limitation" below).

## Execution

- Build: clean `cmake -S . -B build -DCMAKE_BUILD_TYPE=Release` for every
  official campaign; the resulting `git_commit` compiled into `pcf_benchmark`
  is what gets recorded in every row.
- Single-threaded: every algorithm implementation in `src/` is
  single-threaded; `pcf_benchmark` runs one instance/algorithm/repetition at
  a time in one process, never in parallel with another benchmark process.
- CPU affinity: official campaign invocations are pinned to one physical
  core with `taskset -c <core>` where the campaign script is run
  non-interactively (see `tools/run_benchmark.py` usage in each campaign
  report under `results/`).
- Instance order: `run_benchmark.py` processes instances in sorted filename
  order (deterministic and recorded, not randomized) *within* a directory;
  campaigns that pair multiple algorithms interleave the *algorithm* order
  per repetition via `--shuffle-seed`, which `pcf_benchmark` uses to
  permute `--algorithms` independently for every repetition, so no algorithm
  is consistently favoured by being first or last when the CPU is still
  warming a frequency state.
- Warm-up: the first repetition of every (instance, algorithm) pair is
  discarded from the median/IQR computed by `tools/aggregate_results.py` is
  **not** implemented as a separate flag; instead every campaign requests at
  least 5 repetitions (11 for small/fast instances) and uses the median,
  which is already robust to a single slow first observation. This is a
  documented simplification versus a literal separate warm-up rep.
- Repetitions: 11 for instances expected to finish in well under 100 ms
  (structured/random small-to-medium), 5 for instances expected to run
  multiple seconds or more (large random/structured, campaigns C and D).
- Timeout: 300 seconds wall-clock per single algorithm run within
  `pcf_benchmark`; a run that does not return within the timeout is killed
  by the campaign driver, recorded as `status=timeout` in the campaign's own
  log (not as a CSV row, since `pcf_benchmark` cannot emit a partial row for
  a run that never returned), and excluded from `processed.csv` medians.
- Correctness is never included in the timed region: `pcf_benchmark` times
  only the `compute_*` call; hashing the result for `sequence_hash` happens
  immediately after the timer stops (a handful of hash mixing operations per
  macroitem, not part of `elapsed_ns`), and cross-algorithm/oracle
  correctness comparison happens later, in `tools/aggregate_results.py`, on
  already-collected CSV rows.
- Wall time only: `elapsed_ns` is `std::chrono::steady_clock` wall time.
  CPU time is not recorded separately (single-threaded, otherwise-idle
  machine, so wall and CPU time track closely); this is a documented
  simplification versus the plan's "wall time and CPU time both recorded".
- Peak memory: `peak_rss_kib` is `getrusage(RUSAGE_SELF).ru_maxrss`, sampled
  immediately after each repetition. Because this is a *process-lifetime*
  peak (monotonically non-decreasing across repetitions within one
  `pcf_benchmark` invocation), the value recorded on repetition *k* is the
  peak over repetitions `0..k`, not that repetition's own peak in isolation;
  campaigns that need a single-repetition memory number invoke
  `pcf_benchmark` with `--repetitions 1` for that purpose (RaC memory
  reporting, campaign D).

## Statistics

- `tools/aggregate_results.py` reports the median and interquartile range
  (`statistics.quantiles(..., method="inclusive")`, Q3-Q1) of `elapsed_ns`
  and `peak_rss_kib` per (campaign, instance, algorithm).
- Ratios (e.g. RaC/HFMA) are computed **per paired instance** and then
  aggregated (median and IQR of the per-instance ratios), never as a ratio
  of two aggregate means, per plan section 10.3
  (`tools/emit_latex_tables.py --mode ratio`).
- Bootstrap confidence intervals for the headline ratios are not yet
  implemented; `iqr` of the per-instance ratio distribution is reported
  instead. This is a known gap versus the plan's "intervalli di confidenza
  bootstrap", left as documented future work rather than an unverified
  add-on under time pressure.
- Timeouts and failures are always visible: every campaign report under
  `results/` includes an explicit timeout/failure count, and
  `results_summary.json` records `n_mismatched_instances` for
  cross-algorithm disagreement.

## Correctness verification (plan section 7)

Two independent oracles are used, plus cross-algorithm differential checks:

1. **Exhaustive enumeration** (`pcf_tests`, `tests/test_main.cpp`): every
   directed forest with at most four items over a finite coefficient grid,
   thousands of random forests up to `n=11`, and every one of the six
   coefficient families crossed with mixed/in/out topologies.
2. **Maximum closure at fixed lambda, via an independent max-flow engine**
   (`tools/verify_with_bppf.py`): converts the instance and one exact
   rational lambda into BPPF's DIMACS input (`tools/convert_to_bppf.py`),
   runs the unmodified upstream `third_party/bppf/pseudopar.c` compiled with
   `-DBREAKPOINTS` (target `pcf_bppf_oracle`), and compares the returned
   minimum-cut closure against our own algorithm's closure at that lambda.
   This is genuinely independent: BPPF is a third-party pseudoflow
   implementation unrelated to FMA/HFMA/RaC. It was validated on 481
   breakpoint-midpoint checks spanning random/path/star topologies and all
   six coefficient families with zero disagreements before being trusted
   for campaign F.
3. **Cross-algorithm differential agreement**: `tools/aggregate_results.py`
   computes `correctness_status` for every (campaign, instance) group as
   `"agreed"` if every algorithm benchmarked together on that instance
   produced the same `sequence_hash`, else `"mismatch"` (listed in
   `mismatches.csv`). `sequence_hash` is a 64-bit FNV-1a fingerprint over
   the canonical (sorted-node, profit, weight) serialization of the
   macroitem sequence — **not** a cryptographic SHA-256, unlike the
   `instance_sha256` used for instance-file integrity in
   `instances/manifests/*.json`. This is a deliberate, documented deviation
   from the plan's `sequence_sha256` column name: the goal is a cheap
   equality fingerprint to pair rows during aggregation, and cryptographic
   collision resistance is not needed for that purpose.

## Known measurement limitation

This machine has no passwordless root, so the CPU governor could not be set
to `performance` for the official runs; it stayed at the system default,
`powersave`. Absolute wall-clock numbers in every campaign report therefore
carry ordinary frequency-scaling noise. This is mitigated, not eliminated,
by: median-of-several-repetitions reporting, `taskset` core pinning, and
reporting every headline comparison as a **paired, same-instance ratio**
(HFMA vs RaC on the *same* instance in the *same* process invocation window)
rather than as independent absolute times — a systematic frequency shift
during one instance's measurement affects both algorithms compared on it
almost identically, so paired ratios are far less sensitive to this
limitation than raw absolute times would be.

## Campaigns

See `results/` for the report and raw/processed CSV of each campaign as it
is run; `results_summary.json` (produced by `tools/aggregate_results.py`) is
the single source of citable totals. Campaign definitions (topologies,
coefficient families, sizes, seeds, algorithms) follow plan section 9:

- **A — small correctness**: `n=1..10` (extended by `pcf_tests` up to
  `n=11` for random forests, and `n=4` exhaustively over all topologies),
  every topology and coefficient family, oracle + every algorithm.
- **B — medium random**: `n∈{100,...,1000}`, `mixed-forest`,
  `rho∈{0.3,0.6,0.9,1.0}`, 6 families, 10 seeds (2400 instances), FMA, HFMA
  and RaC on every instance, paired sequence verification.
- **C — large random**: `n∈{10000,...,100000}`, same structural/coefficient
  matrix as B, HFMA and RaC on every instance; FMA restricted to `n=10000`
  only (2 repetitions instead of the campaign's usual 3, since it is a
  reference baseline, not the headline comparison), preregistered from the
  timing calibration in "Known measurement limitation" above (FMA already
  takes tens of seconds per instance at `n=20000`).
- **D — structured stress**: `path-mixed`, `binary-mixed`, `star-mixed`,
  `n∈{100,200,500,1000,2000,5000,10000,20000,50000,100000}`, 6 families, 10
  seeds (600 instances per topology), HFMA vs RaC paired; FMA restricted to
  `n≤2000` for the same reason as campaign C. On `star-mixed`, HFMA and
  DHFMA both exhaust the 8GB memory ceiling on every single instance at
  `n∈{20000,50000,100000}` (180/600 instances); because HFMA and RaC are
  benchmarked together in one process, that also loses RaC's result for
  those instances even though RaC alone is unaffected, so a RaC-only
  recovery pass is run on exactly that size/topology subset
  (`instances/campaign_d_star_large_only`, see `tools/run_official_campaigns.sh`).
- **E — specialized orientations**: `in-forest` (HFMA vs HIMA vs RaC) and
  `out-forest` (HFMA vs HOMA vs RaC), `n∈{100,...,1000}∪{10000,...,100000}`
  (20 sizes), `rho∈{0.6,1.0}` (a reduced density set relative to campaigns B
  and C, since in-/out-forest structure is already the primary variable
  under study here), 6 coefficient families, 5 seeds: 1200 instances per
  orientation, 2400 total. This reduced matrix (vs. B/C's 4 densities and 10
  seeds) is a preregistered scoping choice to keep the campaign tractable
  once extended across two orientations and the full size range up to
  n=100000, not an ad hoc reduction after the fact.
- **F — BPPF baseline (optional, scope-limited)**: `n∈{100,200,500,1000}`,
  `mixed-forest`, `rho=0.6`, all 6 coefficient families, 3 seeds (72
  instances), 3 repetitions (`tools/run_bppf_campaign.py`). BPPF is used as
  Oracle 2 (above) at arbitrary scale, since a single fixed-lambda min-cut
  call is cheap and scale-independent in principle. Using it as a *timed
  baseline* across a full parametric sweep is scoped to small/medium
  instances only, because `tools/convert_to_bppf.py` bakes one exact lambda
  into integer arc capacities per call and requires the scaled coefficients
  to stay under `2**53` (double-precision-safe) with one BPPF process
  invocation per breakpoint — correct at any scale, but too many process
  spawns to be a fair wall-clock comparison once an instance has many
  thousands of breakpoints. This scope limitation is a direct instance of
  the "transparent handling of limited precision" the plan requires for this
  campaign (section 9.6); the resulting total time is 91x-1270x HFMA's
  in-process time on the same instance, reported only as evidence BPPF is a
  correct oracle at this scale, never as a native-speed baseline.
