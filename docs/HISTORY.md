# History

This file records how this repository came to exist and how the official
benchmark campaigns were produced. It is the only narrative/process document
in `docs/`; every other file there is a reference document describing the
current state of the code, not how it got there.

## Origin

This codebase is an independent rewrite of the algorithms first developed
for "On parametric Maximum Closure Problems over precedence forests"
(Dose, Furini, Locatelli). The original implementation lived in a
workspace shared with an unrelated precedence-constrained-knapsack project;
before any computational result could be trusted for a v2 revision of the
manuscript, the algorithms needed a from-scratch, audited, independently
testable home with no path or build dependency on that legacy workspace.
`PROVENANCE.md` records exactly what was ported from the legacy codebase
(the `RaC` implementation) and how its equivalence was verified
(`docs/RAC_AUDIT.md`).

## What was executed, in order

1. **Freeze and separate.** The legacy code and paper were inventoried and
   frozen; this repository was started as a clean directory with no
   dependency on `CODE_FOREST/`, `GITHUB/`, or any other legacy path
   (verified by the clean-clone checklist in `docs/REPRODUCIBILITY.md`).
2. **Independent skeleton.** A closure-specific `Instance` model, `.pcf`
   parser (`docs/INSTANCE_FORMAT.md`), and CMake/CTest/CI were built and
   made to compile and test without access to any legacy directory.
3. **Porting `FMA`/`DFMA`/`HFMA`/`DHFMA`/`HIMA`/`HOMA`.** Ported with
   provenance, all knapsack/capacity semantics removed, checked against the
   exhaustive oracle and each other (`docs/VALIDATION.md`).
4. **Recovering `RaC`.** The rake-and-compress/top-tree implementation was
   extracted from an archived experimental package, audited
   operation-by-operation against both the manuscript and the recovered
   source (`docs/RAC_SPECIFICATION.md`, `docs/RAC_AUDIT.md`), and passed
   through the same oracle, differential and sanitizer checks before being
   trusted for benchmarking.
5. **Generators and instances.** Deterministic generators for the six
   closure-specific affine-coefficient families and six topology families
   were built, each producing SHA-256-manifested, reproducible instances
   (`docs/INSTANCE_FORMAT.md`, `docs/REPRODUCIBILITY.md`).
6. **Pilot experiments.** Small-scale pilot runs (superseded results kept
   for the record in `results/pilot_exploratory/`) estimated per-instance
   timing, informed repetition counts and timeouts, and surfaced the first
   evidence of the `FMA`/`HFMA`-vs-star and `HFMA`/`RaC` crossover effects
   later confirmed at full scale.
7. **Official campaigns A–F.** Run to completion and frozen in
   `docs/EXPERIMENTAL_PROTOCOL.md` before being treated as citable: small
   correctness (A), medium and large random forests (B, C), structured
   stress tests on paths/binary trees/stars (D), specialized in-/out-forest
   orientations (E), and a scope-limited `BPPF` baseline (F). Raw and
   processed output live under `results/`; `results/processed/results_summary.json`
   is the single source of citable totals.
8. **Independent publication.** This repository was packaged as a
   standalone, self-sufficient GitHub repository (`parametric-closure-forests`),
   tagged `v0.1.0`, with instance and result archives attached as release
   assets and verified against a clean clone (`docs/REPRODUCIBILITY.md`).

## Commit timeline

| Commit | Date (UTC+2) | What |
|---|---|---|
| `23f703a` | 2026-08-28 13:52 | Initial independent snapshot: skeleton, ported algorithms |
| `f1d68cc` | 2026-08-28 17:16 | Build fixes, rewritten coefficient families, campaigns B/C/D-path/D-binary/F run |
| `2ed065c` | 2026-08-28 22:19 | Official campaigns B, C, D, E, F and dual variants completed |
| `26a8600` | 2026-08-28 22:21 | Documented `build_report.sh`'s dependency on the released instance archive |
| `3c34793` | 2026-08-28 22:22 | Documented the exact campaign C/D/E/F scoping actually executed |
| `faa6fef` | 2026-08-28 22:33 | Per-instance manifests added for every official campaign |

Release `v0.1.0` was tagged at `3c34793`.

## Superseded pilot work

`results/pilot_exploratory/` holds reports and raw CSVs from before the
official campaign design was frozen. They are kept for the record, not
deleted, and are excluded from every packaged release
(`tools/package_release.sh` zips only `results/raw`, `results/processed`,
`results/tables` and `results/logs`). See
`results/pilot_exploratory/README.md`.

## Relationship to the manuscript

This repository's numbers are integrated into the manuscript's Section 4
(Computational Results); see the manuscript for the scientific narrative
and interpretation, and `docs/VALIDATION.md`/`docs/EXPERIMENTAL_PROTOCOL.md`
here for exactly how each number was produced.
