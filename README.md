# Parametric Closure on Forests — Source Code, Instances & Results

[![C++ validation](https://github.com/fabiofurini/parametric-closure-forests/actions/workflows/ci.yml/badge.svg)](https://github.com/fabiofurini/parametric-closure-forests/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

C++ implementation, benchmark infrastructure, reproducible instances and
raw/processed results for:

> **"On parametric Maximum Closure Problems over precedence forests"**
> Valerio Dose, Fabio Furini, Marco Locatelli

Code, instance generators, benchmark instances and results all live in
this one repository.

The notation follows the manuscript: each vertex has integral profit
$p_i$, strictly positive integral weight $w_i$, and affine contribution
$p_i-\lambda w_i$. A directed arc `(u,v)` means `x_u <= x_v`.

<p align="center">
  <img src="docs/images/closure_layers_example.png" alt="Optimal parametric closure on a 7-vertex example" width="520">
</p>

Each node shows $p_i \mid w_i$, with the small number beside it the vertex
index. For $\lambda$ above 2 the optimal closed set is empty; as $\lambda$
falls past each breakpoint $\lambda_1=2$, $\lambda_2=\tfrac23$,
$\lambda_3=\tfrac12$, one more closure layer becomes worth including, and
the optimal solution only ever grows: $\mathcal M_1=\{1,5\}$, then
$\mathcal M_2=\mathcal M_1\cup\{2,4,7\}$, then
$\mathcal M_3=\mathcal M_2\cup\{3,6\}=\mathcal I$. Every algorithm in this
repository computes this whole nested sequence — all breakpoints and all
closure layers — in one call, rather than solving the plain (non-parametric)
closure problem separately at each $\lambda$.

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

### Memory-bounded HPaC variants, for high-degree inputs

`HPaC`'s heap uses push-only lazy deletion: every time a node's closure sum
changes, all incident edges are re-pushed rather than updated in place, so
stale entries only get discarded lazily. This is $O(n)$ space on typical
inputs, but on a high-degree hub (e.g. the `star-mixed` structured family)
the hub is touched repeatedly and each touch re-pushes one entry per
incident edge, so heap size can grow well past $O(n)$ — confirmed to exhaust
an 8 GB ceiling by `n=20000` on the star class. These two variants solve
exactly that case, each with a different fix for the same root cause:

| Flag | Name | Description |
|---|---|---|
| `hpac_eager` | **HPaC-Eager** | Same algorithm as `hpac`, but the two priority structures are `std::set`-indexed with an erase-then-insert update on every touch, so at most one live entry per edge/node ever exists. |
| `hpac_bounded` | **HPaC-Bounded** | Same lazy heap as `hpac`, but fully rebuilt (stale entries dropped) whenever its size exceeds a constant factor of the live candidate count. |

Both keep `hpac`'s worst-case time bound and are covered by every existing
exhaustive-oracle and differential-testing check in `pcf_tests`. A local
pilot run keeps memory within a few tens of MB on star instances up to
`n=20000`, where plain `hpac` already fails an 8 GB ceiling; the full
star-class campaign confirming this at every size is still pending (see
`docs/EXPERIMENTAL_PROTOCOL.md` once it is run). They are not part of the
main computational study reported in the paper (which uses `hpac`
throughout, as validated on the full official campaigns); use them directly
whenever an input can have a high-degree hub and `hpac`'s memory growth is
a concern.

---

## Quick start

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j
ctest --test-dir build --output-on-failure

build/pcf_solve --instance instances/mixed_tree.pcf --algorithm rac
```

**Input format** (`.pcf`, one-based vertex ids — full
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
| [`docs/INSTANCE_GENERATION.md`](docs/INSTANCE_GENERATION.md) | The six topology families and six affine-coefficient families, and how each is built |
| [`docs/EXPERIMENTAL_PROTOCOL.md`](docs/EXPERIMENTAL_PROTOCOL.md) | Measurement protocol, statistics, and the official campaign design (A–F) |
| [`docs/RAC_SPECIFICATION.md`](docs/RAC_SPECIFICATION.md) | `RaC`'s implementation contract, frozen against the manuscript |
| [`docs/RAC_AUDIT.md`](docs/RAC_AUDIT.md) | Line-by-line audit of the ported `RaC` source against that contract |
| [`docs/REPRODUCIBILITY.md`](docs/REPRODUCIBILITY.md) | Regenerating instances, rebuilding tables, the clean-clone independence checklist, release contents |

---

## Instances, data & reproducibility

Instances and results live in this same repository, alongside the code:

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
