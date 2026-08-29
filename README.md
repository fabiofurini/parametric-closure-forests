# Parametric Closure on Forests — Source Code, Instances & Results

[![C++ validation](https://github.com/fabiofurini/parametric-closure-forests/actions/workflows/ci.yml/badge.svg)](https://github.com/fabiofurini/parametric-closure-forests/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Independent C++ implementation, benchmark infrastructure, reproducible
instances and raw results for:

> **"On parametric Maximum Closure Problems over precedence forests"**
> Valerio Dose, Fabio Furini, Marco Locatelli

This repository is self-contained: code, instance generators, benchmark
instances and raw/processed results all live here under one identity. It
does not compile, read or depend on any other repository at build or run
time (see [`PROVENANCE.md`](PROVENANCE.md)).

The notation follows the manuscript: each vertex has integral profit
$p_i$, strictly positive integral weight $w_i$, and affine contribution
$p_i-\lambda w_i$. A directed arc `(u,v)` means `x_u <= x_v`. There is no
capacity anywhere in this repository.

---

## Algorithms

| Flag | Name | Description | Complexity |
|---|---|---|---|
| `pac` | **PaC** | Peel-and-Contract — direct-scan reference algorithm, arbitrary forest orientation | $O(n^2)$ |
| `dpac` | **DPaC** | Dual of `pac` (increasing ratio order) | $O(n^2)$ |
| `hpac` | **HPaC** | Heap-based Peel-and-Contract | $O(n^2\log n)$ worst case, $O(n\log n)$ typical |
| `dhpac` | **DHPaC** | Dual of `hpac` | as `hpac` |
| `hipac` | **HIPaC** | Heap-based In-tree Peel-and-Contract (in-forests only) | $O(n\log n)$ |
| `hopac` | **HOPaC** | Heap-based Out-tree Peel-and-Contract (out-forests only) | $O(n\log n)$ |
| `rac` | **RaC** | Rake-and-Compress / top-tree algorithm, any tree | $O(n\log n)$ |
| — | **BPPF** | Bounded-Precision Parametric Pseudoflow (Hochbaum et al.), third-party independent oracle | — |

`PaC`'s two moves (peel the current best final vertices, contract an arc)
are the same pair as `RaC`'s own rake/compress, under a direct-scan or
lazy-heap schedule instead of balanced top-tree rounds. Every algorithm
returns the same object: the ordered sequence of closure layers with exact
rational thresholds, computed with exact integer/rational arithmetic
throughout — no floating point in any decision path.

---

## Quick start

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j
ctest --test-dir build --output-on-failure

build/pcf_solve --instance instances/mixed_tree.pcf --algorithm rac
```

**Input format** (`.pcf`, one-based vertex ids, no capacity field — full
grammar in [`docs/INSTANCE_FORMAT.md`](docs/INSTANCE_FORMAT.md)):

```text
pcf 1
n 4
profits 10 3 8 -2
weights 2 1 4 1
arcs 3
1 2
3 2
4 3
```

---

## Repository structure

```text
include/, src/     C++ library, CLI solver (pcf_solve) and benchmark runner (pcf_benchmark)
tests/             CTest suite (pcf_tests) — exhaustive oracle + differential checks
tools/             instance generators, benchmark runner, BPPF converter/verifier,
                   aggregation/reporting/packaging pipeline (Python + shell)
third_party/bppf/  unmodified upstream BPPF source — independent max-flow oracle
instances/         committed small fixtures + manifests; bulk archives are
                   generated, not committed (see docs/REPRODUCIBILITY.md)
results/           raw and processed campaign data, LaTeX table fragments
report/            standalone technical report (companion to the manuscript)
docs/              full documentation — see below
```

For the full module-by-module breakdown, see
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## Documentation

Each topic has its own page:

| Page | Covers |
|---|---|
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Code layout, algorithm signatures, data model, executables, analysis pipeline |
| [`docs/VALIDATION.md`](docs/VALIDATION.md) | The three independent correctness layers (exhaustive oracle, BPPF max-flow oracle, cross-algorithm differential testing), sanitizers, CI |
| [`docs/INSTANCE_FORMAT.md`](docs/INSTANCE_FORMAT.md) | The `.pcf` file grammar |
| [`docs/EXPERIMENTAL_PROTOCOL.md`](docs/EXPERIMENTAL_PROTOCOL.md) | Measurement protocol, statistics, and the official campaign design (A–F) |
| [`docs/RAC_SPECIFICATION.md`](docs/RAC_SPECIFICATION.md) | `RaC`'s implementation contract, frozen against the manuscript |
| [`docs/RAC_AUDIT.md`](docs/RAC_AUDIT.md) | Line-by-line audit of the ported `RaC` source against that contract |
| [`docs/REPRODUCIBILITY.md`](docs/REPRODUCIBILITY.md) | Regenerating instances, rebuilding tables, the clean-clone independence checklist, release contents |
| [`PROVENANCE.md`](PROVENANCE.md) | What was ported from the legacy PCKP codebase, and how equivalence was verified |

---

## Instances, data & reproducibility

Unlike a typical split between a code repository and a data repository,
**instances and results live in this same repository**:

- `instances/manifests/*.json` — deterministic identifier, topology
  classification, coefficient bounds and SHA-256 checksum for every
  instance, so any regenerated or downloaded archive can be verified
  byte-for-byte (`docs/REPRODUCIBILITY.md`).
- `results/raw/*.csv` — one immutable row per (instance, algorithm,
  repetition), produced by `pcf_benchmark`.
- `results/processed/` and `results/tables/*.tex` — aggregated medians/IQRs
  and the exact LaTeX table fragments used in the manuscript and the
  technical report; regenerated from raw data by `tools/build_report.sh`,
  never hand-typed.

Bulk instance archives (up to $n=100\,000$) and the matching raw/processed
results are attached to
[**GitHub releases**](https://github.com/fabiofurini/parametric-closure-forests/releases)
rather than committed to git history. See
[`docs/REPRODUCIBILITY.md`](docs/REPRODUCIBILITY.md) for the exact
regeneration commands, the full campaign pipeline
(`tools/run_official_campaigns.sh`, `tools/run_bppf_campaign.py`,
`tools/build_report.sh`, `tools/package_release.sh`), and the release
contents.

---

## Citation

See [`CITATION.cff`](CITATION.cff).
