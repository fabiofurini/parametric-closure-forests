# Provenance

Every piece of code in this repository that originated outside it, what was
changed on the way in, and how the result was verified. This repository does
not compile, import or read any file from the workspace it was extracted
from: everything below was copied once, adapted, and is maintained here.

## RaC (rake-and-compress / top-tree algorithm)

- **Source**: `algo_top_tree.cpp` (518 lines) and `algo_top_tree.hpp`, from an
  archived experimental package (`top_tree_cpp_experiment_package`) produced
  while the algorithm was being developed. That package is preliminary
  experimental material, not an accepted dependency; see
  `docs/RAC_SPECIFICATION.md`.
- **Destination**: `src/rac.cpp`, and `RaCStats` in
  `include/parametric_closure/algorithms.hpp`.
- **Transformation**: a line-by-line diff shows the port is verbatim except
  for two changes:
  1. renames only — namespace `macroitems` → `pcf`, class `TopTreeSolver` →
     `RaCSolver`, struct field `items` → `layers` (the last one renamed again
     here when "macroitem" became "closure layer");
  2. the entry point no longer stores profits and weights as `long double`
     with a `1e-9` rounding tolerance. It takes the instance's native
     `std::int64_t` coefficients directly, removing a floating-point
     round-trip the old code needed only because its own instance type stored
     coefficients as `long double`. `pcf::Instance` stores exact 64-bit
     integers, so the tolerance check was unnecessary and was dropped rather
     than ported.
  No cluster, envelope, `Compress1`/`Compress2`/`Rake`, round-selection or
  top-down-recovery logic was changed. The full diff and an
  operation-by-operation audit against the manuscript are in
  `docs/RAC_AUDIT.md`.
- **Verification**: `pcf_tests` runs RaC against the exhaustive
  closure-enumeration oracle on every directed forest with at most four
  vertices over a finite coefficient grid; against PaC/DPaC/HPaC/DHPaC on
  deterministic random forests and on the six coefficient families crossed
  with mixed/in/out topologies; and under AddressSanitizer and
  UndefinedBehaviorSanitizer. See `docs/RAC_AUDIT.md`, "Acceptance evidence".

## PaC, DPaC, HPaC, DHPaC, HIPaC, HOPaC

- **Source**: the direct-scan and heap-based closure-layer algorithms for
  directed forests developed for the manuscript's own computational study,
  "On parametric Maximum Closure Problems over precedence forests" (Dose,
  Furini, Locatelli), previously maintained in a separate repository.
- **Destination**: `src/pac.cpp`, `src/dpac.cpp`, `src/hpac.cpp`,
  `src/dhpac.cpp`, `src/hipac.cpp`, `src/hopac.cpp`.
- **Transformation**: re-expressed directly against `pcf::Instance` (signed
  integral profit, strictly positive integral weight, directed forest arcs)
  with no knapsack capacity, no LP relaxation and no split-item
  reconstruction. Ratio comparisons use the exact 128-bit cross-multiplication
  in `include/parametric_closure/rational.hpp`.
- **Verification**: the same CTest suite as RaC — exhaustive oracle,
  cross-algorithm differential tests, and the HIPaC-on-in-forest /
  HOPaC-on-out-forest checks.

## FPHPF (fully parametric pseudoflow — the comparison baseline)

- **Source**: <https://github.com/hochbaumGroup/pseudoflow-parametric-cut-v2>,
  commit `fbd480fb1c4215792768b2a22f01d731a9fb6a27` (2025-05-27): Hochbaum's
  *fully parametric* HPF solver, which is given only a parameter range and
  locates every breakpoint itself. Files taken: `src/pseudoflow/c/hpf.c`,
  `src/pseudoflow/core/libhpf.{c,h}` and `LICENSE.md`.
- **Destination**: `third_party/fphpf/`, keeping the upstream `c/` and `core/`
  layout so no include path changes. Built as the standalone `pcf_fphpf`
  executable; never linked into `libpcf`.
- **License**: UC Berkeley research license, reproduced verbatim in
  `third_party/fphpf/LICENSE.md` as it requires. Created by Quico Spaen and
  Dorit S. Hochbaum, modified by Ayleen Irribarra.
- **Transformation**: two `printf` format strings, and nothing else, recorded
  as `third_party/fphpf/local.patch` — the timing line `%.3lf` → `%.9lf`, and
  the per-group parameter line `%lf` → `%.17g`. No algorithmic line is
  touched. `third_party/fphpf/UPSTREAM_README.md` explains why each digit
  matters, documents the solver's output semantics (which do not follow its
  own README), records the fixed `TOL = 1E-7` that merges closure layers
  closer than about `2e-7`, quotes the caveat its authors state about using it
  for comparison, and gives the exact encoding and command by which this
  repository drives it.
- **Role and verification**: competitor in a timed race (campaign H), never a
  correctness oracle. `tools/race_fphpf.py` compares the partition it returns
  with HPaC's on every instance and recomputes all breakpoints exactly from
  that partition; the two agree on 2,400/2,400 instances with `n <= 1000`.
  Correctness of the algorithms in this repository is established
  independently of it (`docs/VALIDATION.md`).

## BPPF (removed 2026-09-08)

The bounded-precision *simple* parametric solver
(<https://github.com/hochbaumGroup/Bounded-precision-simple-parametric>,
`pseudopar.c`) was the comparison baseline of every earlier version of this
study. It only evaluates minimum cuts at caller-supplied parameter values, so
the comparison had to hand it the `k+1` probe values bracketing HPaC's own
exact thresholds — a protocol that cannot be made self-contained without
either a uniform grid of `1e6`–`1e9` probes or an adaptive driver that
destroys the warm start its efficiency depends on. The fully parametric
solver above makes it unnecessary. `third_party/bppf/`, the tools
`convert_to_bppf_sequence.py` and `run_bppf_native_campaign.py`, the CMake
targets `pcf_bppf`/`pcf_bppf_oracle` and campaign G's data were deleted; all
of it remains in git history at tag `v0.3.0`.

## Instance generators

- **Source**: the statistical shape only (topology density, structured
  families) of an earlier test bed.
- **Destination**: `tools/generate_random_instances.py`,
  `tools/generate_structured_instances.py`, `tools/pcf_families.py`.
- **Transformation**: coefficients are **not** reproduced from those
  generators. They are drawn from scratch under the six closure-specific
  affine families defined in `tools/pcf_families.py`
  (`independent-positive`, `independent-signed`, `correlated`,
  `anti-correlated`, `near-ties`, `exact-ties`), motivated only by the shape
  of the resulting `p/w` ratios and with no reference to knapsack correlation
  classes.

## Instances: regenerated, not converted

Every instance used in the official campaigns is regenerated, never converted
from an older file:

- topologies (`mixed-forest`/`mixed-tree`, `in-forest`, `out-forest`,
  `path-mixed`, `binary-mixed`, `star-mixed`) come from the generators in
  `tools/`, seeded deterministically and manifested with SHA-256 checksums in
  `instances/manifests/`;
- coefficients are freshly drawn from the six families above, not copied or
  rescaled;
- no conversion tool exists here, because none is needed: the older format
  held the same two coefficient arrays this repository already produces from
  its own seeded generators, so a byte-level converter would only reproduce
  numbers we generate anyway.

Every released archive is reproducible from `tools/` plus the recorded seeds,
and is checksummed; see `docs/REPRODUCIBILITY.md`.
