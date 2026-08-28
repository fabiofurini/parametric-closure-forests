# Provenance

This file tracks every piece of code and every instance family in this
repository that originated outside it, as required by
`docs/PIANO_PARTE_COMPUTAZIONALE.md` sections 2.3 and 3. This repository does
not compile, import or read any file from the legacy PCKP workspace at
runtime; everything listed below was copied once, adapted, and is now
maintained independently.

## Code provenance

### RaC (rake-and-compress / top-tree algorithm)

- **Source**: `MACROITEMS_PAPER/LLMs/CONTROPROSTA_DI_CHAT/TESTS_CHAT/top_tree_cpp_experiment_package.zip`,
  file `code/algo_top_tree.cpp` (518 lines) and `code/algo_top_tree.hpp`,
  packaged inside `LLM_PROPOSTE_SEPARAZIONI_PAPERI.tar.gz` in the parent
  workspace. That package is preliminary experimental material, not an
  accepted dependency (see `docs/RAC_SPECIFICATION.md`).
- **Destination**: `src/rac.cpp`, `RaCStats` in
  `include/parametric_closure/algorithms.hpp`.
- **Transfer date**: 2026-08-28.
- **Transformation**: a line-by-line diff between the legacy source and
  `src/rac.cpp` shows the port is verbatim except for:
  1. namespace `macroitems` -> `pcf`, class `TopTreeSolver` -> `RaCSolver`,
     struct field `items` -> `macroitems` (cosmetic renames only);
  2. the public entry point no longer stores `profit`/`weight` as `long
     double` with a `1e-9` rounding tolerance; it takes the instance's native
     `std::int64_t` profits and weights directly. This removes a
     floating-point round-trip that the legacy code needed only because its
     `Instance` type stored coefficients as `long double`; the new
     `pcf::Instance` stores them as exact 64-bit integers, so the tolerance
     check is unnecessary and was dropped rather than ported.
  No cluster, envelope, `Compress1`/`Compress2`/`Rake`, round-selection or
  top-down-recovery logic was changed. The full diff and an operation-by-operation
  audit against the manuscript are in `docs/RAC_AUDIT.md`.
- **Verification**: `pcf_tests` (CTest) exercises RaC against the exhaustive
  closure-enumeration oracle on every directed forest with at most four
  items over a finite coefficient grid, against FMA/DFMA/HFMA/DHFMA on
  deterministic random forests and on the six coefficient families crossed
  with mixed/in/out topologies, and against sanitizer builds. See
  `results/TEST_REPORT_2026-08-28.md` and `docs/RAC_AUDIT.md` section
  "Acceptance evidence".

### FMA, DFMA, HFMA, DHFMA, HIMA, HOMA

- **Source**: the direct-scan and heap-based macroitem algorithms for
  directed forests developed for the PCKP/LP paper's computational study
  (arXiv v1, `PAPER_MARCO/macroitems_v1_with_appendix.tex`).
- **Destination**: `src/fma.cpp`, `src/dfma.cpp`, `src/hfma.cpp`,
  `src/dhfma.cpp`, `src/hima.cpp`, `src/homa.cpp`.
- **Transfer date**: 2026-08-28 (prior to the audit that produced this file;
  the port predates the CMake/BPPF build fix recorded in the first commit).
- **Transformation**: re-expressed directly against `pcf::Instance` (signed
  integral profit, positive integral weight, directed forest arcs) with no
  knapsack capacity, no LP relaxation and no split-item reconstruction. Ratio
  comparisons use the exact 128-bit cross-multiplication in
  `include/parametric_closure/rational.hpp`.
- **Verification**: same CTest suite as RaC (exhaustive oracle, cross-algorithm
  differential tests, HOMA-on-out-forest and HIMA-on-in-forest checks).

### BPPF (parametric pseudoflow baseline)

- **Source**: `third_party/bppf/pseudopar.c`, upstream bounded-precision
  parametric pseudoflow implementation, recorded unmodified with its own
  `third_party/bppf/UPSTREAM_README.md`.
- **Destination**: built as the standalone `pcf_bppf` executable; never
  linked into `libpcf`.
- **Transformation**: none to the algorithm itself. A converter from the
  `.pcf` format to the BPPF input format is provided as
  `tools/convert_to_bppf.py` and never encodes a capacity or PCKP semantics.
- **Status**: campaign F (general parametric-flow baseline) is optional per
  the plan and is run only if explicitly requested for the manuscript.

### Instance generators

- **Source**: the statistical shape (topology density, structured families)
  of the legacy PCKP test bed generators.
- **Destination**: `tools/generate_random_instances.py`,
  `tools/generate_structured_instances.py`, `tools/pcf_families.py`.
- **Transformation**: coefficients are **not** reproduced from the legacy
  generators. They are regenerated from scratch under the six
  closure-specific affine families defined in
  `docs/PIANO_PARTE_COMPUTAZIONALE.md` section 8.3 (`independent-positive`,
  `independent-signed`, `correlated`, `anti-correlated`, `near-ties`,
  `exact-ties`), motivated only by the shape of the resulting `p/w` ratios,
  with no reference to knapsack correlation classes. See "Instance migration
  decision" below.

## Instance migration decision

Plan section 17, item 13 leaves open whether historical instances are
converted file-by-file or regenerated. This repository chooses
**regeneration**, not conversion, for every instance used in the official
campaigns:

- topologies (`mixed-forest`/`mixed-tree`, `in-forest`, `out-forest`,
  `path-mixed`, `binary-mixed`, `star-mixed`) are regenerated with the
  generators in `tools/`, seeded deterministically and manifested with
  SHA-256 checksums (`instances/manifests/`);
- coefficients are freshly drawn from the six families above, not copied or
  rescaled from legacy `profits`/`weights` files;
- no `convert_legacy_instances` tool exists in this repository because no
  legacy `.pcf`-shaped file is read: the legacy instance format used
  `profits`/`weights` text files with the *same* two coefficient arrays this
  repository already regenerates independently, so a byte-level converter
  would only reproduce numbers this repository already produces from its own
  seeded generators.

Every official archive is reproducible from `tools/` plus the recorded seeds
and is checksummed in `instances/manifests/`; see `docs/REPRODUCIBILITY.md`.

## What this repository does not depend on

`PAPER/`, `CODE_FOREST/`, `CODE_PARAMETRIC_PSEUDOFLOW/`, `GITHUB/` and the
rest of the parent workspace are not build inputs, not runtime inputs and are
not referenced by path anywhere in `CMakeLists.txt`, `src/`, `include/` or
`tools/`. Section 14.1.1 of the plan requires a clean-clone independence test
before publication; its checklist and result are recorded in
`docs/REPRODUCIBILITY.md`.
