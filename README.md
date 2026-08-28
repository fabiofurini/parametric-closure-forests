# Parametric Closure — computational project

This is the independent C++ codebase for the computational part of the
parametric maximum-closure paper on directed forests.  It does not compile,
read or depend on the historical PCKP project.

The notation follows the manuscript: each item has integral profit \(p_i\),
strictly positive integral weight \(w_i\), and affine contribution
\(p_i-\lambda w_i\).  A directed arc `(u,v)` means `x_u <= x_v`.

## Layout

- `include/`, `src/`: C++ library and command-line solver;
- `tests/`: CTest differential and structural checks;
- `instances/`: new closure-format instances;
- `docs/`: the validated plan and the RaC specification traceability record.
- `instances/manifests/`: deterministic instance metadata and SHA-256 checksums.

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

`pcf_tests` checks FMA/DFMA/HFMA/DHFMA/RaC agreement on a mixed tree,
exhaustively on every directed forest with at most four items over a finite
coefficient grid, and on deterministic random forests. It uses an independent
closure-enumeration oracle on all small cases, verifies HOMA on out-forests,
and checks partition, strict ratio ordering and closure-prefix invariants.

RaC is specified against the manuscript in
[`docs/RAC_SPECIFICATION.md`](docs/RAC_SPECIFICATION.md). It must continue to
pass these checks before it is used in a benchmark campaign.

## Instance manifests

Build or verify a deterministic manifest for one instance directory with:

```bash
python3 tools/build_instance_manifest.py --instances instances/structured/star_pilot --output /tmp/star.json
python3 tools/build_instance_manifest.py --instances instances/structured/star_pilot --verify /tmp/star.json
```

The committed manifests record the stable identifier, topology classification,
coefficient bounds, component count, seed when encoded in the filename, and
the SHA-256 checksum of every `.pcf` file.
