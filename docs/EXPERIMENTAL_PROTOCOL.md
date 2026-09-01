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
  closure layer, not part of `elapsed_ns`), and cross-algorithm/oracle
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
- Ratios (e.g. RaC/HPaC) are computed **per paired instance** and then
  aggregated (median and IQR of the per-instance ratios), never as a ratio
  of two aggregate means
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

## Correctness verification

One independent oracle is used, plus cross-algorithm differential checks
(`docs/VALIDATION.md`; BPPF plays no verification role — it appears only
as the timed comparison baseline of campaign G):

1. **Exhaustive enumeration** (`pcf_tests`, `tests/test_main.cpp`): every
   directed forest with at most four items over a finite coefficient grid,
   thousands of random forests up to `n=11`, and every one of the six
   coefficient families crossed with mixed/in/out topologies.
2. **Cross-algorithm differential agreement**: `tools/aggregate_results.py`
   computes `correctness_status` for every (campaign, instance) group as
   `"agreed"` if every algorithm benchmarked together on that instance
   produced the same `sequence_hash`, else `"mismatch"` (listed in
   `mismatches.csv`). `sequence_hash` is a 64-bit FNV-1a fingerprint over
   the canonical (sorted-node, profit, weight) serialization of the
   closure layer sequence — **not** a cryptographic SHA-256, unlike the
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
(HPaC vs RaC on the *same* instance in the *same* process invocation window)
rather than as independent absolute times — a systematic frequency shift
during one instance's measurement affects both algorithms compared on it
almost identically, so paired ratios are far less sensitive to this
limitation than raw absolute times would be.

## Campaigns

See `results/` for the report and raw/processed CSV of each campaign as it
is run; `results_summary.json` (produced by `tools/aggregate_results.py`) is
the single source of citable totals. Campaign definitions (topologies,
coefficient families, sizes, seeds, algorithms) are as follows:

- **A — small correctness**: `n=1..10` (extended by `pcf_tests` up to
  `n=11` for random forests, and `n=4` exhaustively over all topologies),
  every topology and coefficient family, oracle + every algorithm.
- **B — medium random**: `n∈{100,...,1000}`, `mixed-forest`,
  `rho∈{0.3,0.6,0.9,1.0}`, 6 families, 10 seeds (2400 instances), PaC, HPaC
  and RaC on every instance, paired sequence verification.
- **C — large random**: `n∈{10000,...,100000}`, same structural/coefficient
  matrix as B, HPaC and RaC on every instance; PaC and DPaC restricted to
  the two smallest sizes of this test bed, `n=10000`
  (`instances/campaign_c_n10000_subset`, 2 repetitions) and `n=20000`
  (`instances/campaign_c_n20000_subset`, 3 repetitions), since they are a
  reference baseline, not the headline comparison, and already take
  hundreds of milliseconds (`n=10000`) to over a second (`n=20000`) per
  instance — measured after fixing the `PaC`/`DPaC` performance regression
  of commit `461fea9`. DHPaC is run on the full `n∈{10000,...,100000}`
  range like HPaC.
- **D — structured stress**: `path-mixed`, `binary-mixed`, `star-mixed`,
  `n∈{100,200,500,1000,2000,5000,10000,20000,50000,100000}`, 6 families, 10
  seeds (600 instances per topology). Path/binary: HPaC vs RaC paired, plus
  DHPaC, with PaC/DPaC restricted to `n≤2000` (same rationale as campaign
  C). Star (plan V3 decisions #4/5bis, `docs/EXPERIMENTAL_PLAN_V3.md`):
  HPaC,RaC paired and DHPaC on `n≤20000`
  (`instances/campaign_d_star_small`, preregistered cutoff — HPaC/DHPaC's
  n² time trend is established there), RaC alone on `n∈{50000,100000}`
  (`instances/campaign_d_star_large_only`), and **PaC on the full size
  range** (cheap on stars). Since HPaC/DHPaC use the bounded-rebuild heap
  (O(n) space), no memory censoring occurs anywhere; in the V3 sweep no
  star run hit the time cap either.
- **E — specialized orientations**: `in-forest` (HPaC vs HIPaC vs RaC) and
  `out-forest` (HPaC vs HOPaC vs RaC), `n∈{100,...,1000}∪{10000,...,100000}`
  (20 sizes), `rho∈{0.3,0.6,0.9,1.0}`, 6 coefficient families and 10 seeds:
  4,800 instances per orientation, 9,600 total. This is the same density and
  seed matrix used by campaigns B/C and by the corresponding experiment in
  the v1 manuscript; it avoids confounding the comparison of the specialized
  algorithms with a change in density coverage.
- **G — BPPF native comparison (v1-style)**: the full campaign-B test bed
  (2,400 `mixed-forest` instances, `n∈{100,...,1000}`), 5 repetitions,
  `prec=1e-6` (`tools/run_bppf_native_campaign.py`). One `pcf_bppf`
  process per instance sweeps the k+1 probe values bracketing all k
  breakpoints in BPPF's native affine encoding — the same methodology as
  the v1 manuscript, and the most favorable setting for BPPF, since it is
  spared the search for the breakpoints. Timing compares BPPF's own
  cumulative solve timer against `hpac`'s in-process time on the same
  instance. Outside the timed region, one `pcf_bppf_oracle` run per
  instance checks closure agreement at every probe; deviations are
  classified as fixed-point tolerance artifacts (reported as a count) or
  genuine disagreements (which invalidate that instance's timing).
  Instances rejected by the encoding's `2**53` representation guard are
  skipped with a printed reason and counted per size/family. See
  `docs/EXPERIMENTAL_PLAN_V3.md` for the full preregistered design.
