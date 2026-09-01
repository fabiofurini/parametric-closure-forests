# Validation

This document describes how correctness of every algorithm in this
repository is established, independently of any single implementation and
before any timing claim. It consolidates the acceptance evidence scattered
across `docs/RAC_AUDIT.md`, `docs/EXPERIMENTAL_PROTOCOL.md` and CI into one
reference. For the measurement protocol (timing, repetitions, statistics),
see `docs/EXPERIMENTAL_PROTOCOL.md`.

## Two independent layers

### 1. Exhaustive enumeration oracle

`tests/test_main.cpp` (`pcf_tests`, run via CTest) checks every algorithm
against an independent oracle that enumerates all closed sets of a small
instance, builds their affine lines `P - lambda*W`, and computes the exact
upper envelope directly — a method structurally unrelated to any algorithm
under test. Coverage:

- every directed forest with at most four items, over a finite
  affine-coefficient grid, exhaustively;
- 10,000 deterministic random directed forests up to 11 items;
- mixed-orientation path, balanced binary and star trees up to 257 items;
- 6,000 deterministic in-forest and 6,000 deterministic out-forest instances,
  plus 2,000 larger instances for each orientation, checked against the oracle
  and cross-checked with `HPaC`/`DHPaC`/`HIPaC`/`HOPaC` as applicable;
- closure layer partition, strict ratio ordering, and closure-prefix invariants.

### 2. Cross-algorithm differential agreement

Every official benchmark campaign (`docs/EXPERIMENTAL_PROTOCOL.md`) runs
multiple algorithms on the same instance and compares their returned
sequences — partition, thresholds and canonical order, not only the
closure layer count. `tools/aggregate_results.py` records
`correctness_status="agreed"` or `"mismatch"` per (campaign, instance)
group; any mismatch is listed explicitly in `mismatches.csv`, never averaged
away. Across the V3 sweep (release v0.3.0: 16,200 instances, 292,080 timed
runs, campaigns B, C, D, E and G): zero disagreements.

## RaC-specific audit

`RaC` (the rake-and-compress/top-tree algorithm) was ported from an
experimental package rather than written from scratch, so it received an
additional operation-by-operation audit before being trusted for
benchmarking:

- `docs/RAC_SPECIFICATION.md` freezes the implementation contract against
  the manuscript (cluster representation, `Compress1`/`Compress2`/`Rake`,
  bottom-up/top-down phases) independently of any specific source file;
- `docs/RAC_AUDIT.md` checks the ported `src/rac.cpp` line-by-line against
  both that contract and the recovered legacy source, covering all twelve
  required correspondence items plus a numerical/overflow/robustness audit,
  and records the exact diff between the legacy source and the ported file
  (two cosmetic renames and one precision-improving change; no logic
  differs).

## Numerical exactness

No algorithm's decision path uses floating-point arithmetic. Every
profit/weight is a signed 64-bit integer; every ratio comparison is a
signed 128-bit cross-multiplication; every rational is stored in reduced
form with a strictly positive denominator. `validate_instance`
(`src/instance.cpp`) rejects any instance whose total absolute profit or
total weight would leave the `INT64_MAX/4` safety margin before any
algorithm runs, so overflow is refused explicitly rather than silently
wrapped.

## Sanitizers and CI

`.github/workflows/ci.yml` builds and runs the full CTest suite on three
configurations for every push and pull request: GCC Release, GCC Debug with
AddressSanitizer + UndefinedBehaviorSanitizer, and Clang Debug. All three
must pass.

## Where the evidence lives

- `results/TEST_REPORT_*.md`: a point-in-time record of a full local
  `pcf_tests` + sanitizer run (machine, toolchain, commands, outcome) —
  not an experimental-results table, a correctness verification record.
- `results/processed/mismatches.csv`: every cross-algorithm disagreement
  ever recorded by an official campaign (empty file if none).
- `results/processed/results_summary.json`: aggregate correctness counts
  (instances benchmarked, timed runs, disagreements) alongside the timing
  results.
