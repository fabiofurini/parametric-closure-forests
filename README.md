# Parametric Closure — computational project

This is the independent C++ codebase for the computational part of the
parametric maximum-closure paper on directed forests.  It does not compile,
read or depend on the historical PCKP project (see `PROVENANCE.md`).

The notation follows the manuscript: each item has integral profit \(p_i\),
strictly positive integral weight \(w_i\), and affine contribution
\(p_i-\lambda w_i\).  A directed arc `(u,v)` means `x_u <= x_v`.

## Layout

- `include/`, `src/`: C++ library and command-line solver/benchmark;
- `tests/`: CTest differential and structural checks;
- `instances/`: closure-format instances (bulk archives are generated, not
  committed — see `docs/REPRODUCIBILITY.md`; `instances/tiny/` and
  `instances/mixed_tree.pcf` are small committed fixtures);
- `instances/manifests/`: deterministic instance metadata and SHA-256 checksums;
- `tools/`: instance generators, the benchmark runner, the BPPF (Oracle 2)
  converter/verifier, and the aggregation/reporting/packaging pipeline;
- `third_party/bppf/`: unmodified upstream bounded-precision parametric
  pseudoflow source, used only as an independent max-flow oracle and
  optional baseline;
- `docs/`: architecture, instance format, validation methodology, RaC audit
  and specification, experimental protocol, and reproducibility instructions;
- `results/`: raw and processed campaign data, LaTeX table fragments;
- `PROVENANCE.md`: what was ported from the legacy PCKP codebase and how it
  was verified; `docs/RAC_AUDIT.md`: the line-by-line audit of the RaC port.

## Build and test

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j
ctest --test-dir build --output-on-failure
```

## Input format

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

Node identifiers in files are one-based. The solver is invoked as:

```bash
build/pcf_solve --instance instances/mixed_tree.pcf --algorithm rac
```

Algorithms `fma`, `dfma`, `hfma`, `dhfma`, `hima`, `homa` and `rac` are C++.
`dhfma` is the dual heap-based FMA for general directed forests. `homa` is the
specialized dual heap method for out-forests, called Heap-based Out-tree
Macroitem Algorithm in the manuscript. Python, when added, is reserved for
reproducible utility scripts and never implements an algorithm. HFMA and DHFMA
use lazy heaps with exact ratio comparisons.

## Current validation

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for how the codebase is
structured and [`docs/VALIDATION.md`](docs/VALIDATION.md) for the full
correctness methodology. Summary:

`pcf_tests` checks FMA/DFMA/HFMA/DHFMA/RaC agreement on a mixed tree,
exhaustively on every directed forest with at most four items over a finite
coefficient grid, and on deterministic random forests. It uses an independent
closure-enumeration oracle on all small cases, verifies HOMA on out-forests,
and checks partition, strict ratio ordering and closure-prefix invariants.

RaC is specified against the manuscript in
[`docs/RAC_SPECIFICATION.md`](docs/RAC_SPECIFICATION.md) and audited
line-by-line against the recovered legacy source in
[`docs/RAC_AUDIT.md`](docs/RAC_AUDIT.md). It must continue to pass these
checks before it is used in a benchmark campaign.

`tools/verify_with_bppf.py` implements the independent max-flow oracle: it
recomputes the maximum closure at a fixed rational lambda with
`third_party/bppf`, an unrelated third-party max-flow/min-cut solver, and
checks agreement with this repository's own algorithms.

## Instance manifests

Build or verify a deterministic manifest for one instance directory with:

```bash
python3 tools/build_instance_manifest.py --instances instances/tiny --output /tmp/tiny.json
python3 tools/build_instance_manifest.py --instances instances/tiny --verify /tmp/tiny.json
```

The committed manifests record the stable identifier, topology classification,
coefficient bounds, component count, seed when encoded in the filename, and
the SHA-256 checksum of every `.pcf` file.

## Official benchmark campaigns

```bash
tools/run_official_campaigns.sh          # campaigns B, C, D, E
python3 tools/run_bppf_campaign.py \
  --pcf-solve build/pcf_solve --pcf-benchmark build/pcf_benchmark \
  --pcf-bppf-oracle build/pcf_bppf_oracle --instances instances/campaign_f \
  --output results/raw/campaign_f_bppf.csv                     # campaign F, scope-limited
tools/build_report.sh                    # validate, aggregate, emit tables
tools/package_release.sh                 # zip instances/ and results/ for a release
```

See `docs/EXPERIMENTAL_PROTOCOL.md` for the full campaign design, measurement
protocol and documented scope limitations, and `docs/REPRODUCIBILITY.md` for
the clean-clone independence checklist.
