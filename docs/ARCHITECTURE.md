# Architecture

How this codebase is structured. For what problem it solves and the
notation, see `README.md`; for the on-disk instance format, see
`docs/INSTANCE_FORMAT.md`.

## Layout

```text
include/parametric_closure/   public C++ headers
  model.hpp                   Rational, node/arc types shared by everything
  instance.hpp                Instance, validate_instance
  algorithms.hpp               compute_pac/dpac/hpac/dhpac/hipac/hopac/rac
                                (plus memory-bounded compute_hpac_eager/_bounded)
  rational.hpp                 exact rational arithmetic (128-bit products)
  pcf.hpp                      .pcf format reader/writer
src/                          implementation, one algorithm per file
  pac.cpp / dpac.cpp           direct-scan reference algorithm and its dual
  hpac_bounded.cpp              the official heap-based HPaC (compute_hpac):
                                 lazy heap periodically rebuilt once past a
                                 size bound, so space is O(n) on every input
  dhpac.cpp                     dual of hpac, same bounded-rebuild policy
  hpac.cpp                      compute_hpac_lazy: the original push-only
                                 lazy-deletion heap, internal reference
  hpac_eager.cpp                hpac with an update-in-place std::set
                                 instead of a lazy-deletion heap
  hipac.cpp / hopac.cpp          specialized heap variants (in-forests/out-forests)
  rac.cpp                      rake-and-compress / top-tree algorithm
  instance.cpp                 instance validation, canonicalization
  cli.cpp                      pcf_solve executable
  benchmark.cpp                 pcf_benchmark executable
  internal/work_graph.hpp      shared internal graph-contraction helper
tests/test_main.cpp           CTest suite (pcf_tests) — see docs/VALIDATION.md
third_party/fphpf/            fetch.sh + local.patch for the upstream fully
                               parametric HPF (Hochbaum group), the comparison
                               baseline; its source is downloaded, not
                               redistributed (see its UPSTREAM_README.md)
tools/                        Python: instance generators, benchmark runner,
                               FPHPF race driver, aggregation/reporting
instances/                    committed small fixtures + manifests;
                               bulk archives are generated, not committed
results/                      raw and processed campaign data, LaTeX tables
docs/                         this documentation
```

## Algorithms

Every algorithm has signature `ClosureLayerSequence compute_*(const Instance&)`
(`RaC` additionally takes an optional `RaCStats*`) and returns the same
canonical object: the ordered sequence of closure layers, each with its exact
rational threshold and member nodes, in non-increasing ratio order.

| Function | Orientation | Time | Space | Notes |
|---|---|---|---|---|
| `compute_pac` | any forest | $O(n^2)$ | $O(n)$ | direct-scan reference |
| `compute_dpac` | any forest | $O(n^2)$ | $O(n)$ | dual of `pac` (increasing order) |
| `compute_hpac` | any forest | $O(n^2\log n)$ worst case, $O(n\log n)$ typical | $O(n)$ | heap-based, bounded-rebuild heap (official) |
| `compute_dhpac` | any forest | as `hpac` | $O(n)$ | dual of `hpac`, same rebuild policy |
| `compute_hipac` | in-forests only | $O(n\log n)$ | $O(n)$ | requires out-degree $\le 1$ |
| `compute_hopac` | out-forests only | $O(n\log n)$ | $O(n)$ | requires in-degree $\le 1$ |
| `compute_rac` | any tree | $O(n\log n)$ | $O(n\log n)$ | rake-and-compress / top-tree |
| `compute_hpac_lazy` | any forest | as `hpac` | $O(\text{touches})$ — $\Theta(n^2)$ on stars | internal reference, see below |
| `compute_hpac_eager` | any forest | as `hpac` | $O(n)$ | `std::set` update-in-place variant |
| `compute_hpac_bounded` | any forest | as `hpac` | $O(n)$ | alias of `compute_hpac` |

`HIPaC`/`HOPaC` assume their required orientation and do not validate it at
runtime; passing a mixed-orientation forest to either is a caller error, not
a checked precondition.

The official `hpac`/`dhpac` keep their lazy-deletion heaps within a
constant factor of the live candidate count by periodic full rebuilds, so
space is genuinely $O(n)$ on every input — matching the manuscript's space
theorem — and measured faster than the pure lazy policy on every topology
tested (docs/EXPERIMENTAL_PLAN_V3.md §2bis). `compute_hpac_lazy` preserves
the original push-only lazy-deletion implementation for reference: it
re-pushes one entry per incident edge at every hub touch without removing
stale ones, which grows to $\Theta(n^2)$ heap entries on a high-degree hub
(the `star-mixed` family).

## Data model

- `Rational`: a reduced fraction with a strictly positive denominator;
  every comparison used in a decision path is a signed 128-bit
  cross-multiplication. No `float`/`double` appears in any algorithm's
  control flow.
- `Instance`: an arc list plus one `int64_t` profit and one strictly
  positive `int64_t` weight per node. `validate_instance` rejects malformed
  instances (non-forest, non-positive weight, overflow risk) before any
  algorithm runs.
- `ClosureLayerSequence`: the shared output type — see above.
- Canonicalization (`pcf::canonicalize`, `src/instance.cpp`): consecutive
  items with an exactly equal threshold are merged into one closure layer. Every
  algorithm uses the same rule, which is part of why cross-algorithm
  differential testing (`docs/VALIDATION.md`) is meaningful.

## Executables

- `pcf_solve --instance FILE --algorithm <pac|dpac|hpac|hpac_eager|hpac_bounded|dhpac|hipac|hopac|rac>`:
  prints the full closure layer sequence for one instance.
- `pcf_benchmark`: times one (instance, algorithm) pair per invocation,
  emitting one CSV row per repetition (`elapsed_ns`, `peak_rss_kib`,
  operation counters for `rac`, `git_commit`, `timestamp_utc`); driven by
  `tools/run_benchmark.py` for a full campaign.
- `pcf_fphpf`: the upstream fully parametric HPF solver
  (`third_party/fphpf/`), used only by the head-to-head race
  `tools/race_fphpf.py` (see README's "The comparison with parametric
  pseudoflow"): one process per instance receives the instance and a
  parameter range (`tools/convert_to_fphpf.py`) and computes all breakpoints
  itself; its partition is compared with `hpac`'s and every breakpoint is
  recomputed exactly from it.

## Analysis pipeline

Unidirectional, no step reads back from a later one:

```text
instance generators (tools/generate_*.py)
  -> instances/ + instances/manifests/*.json (SHA-256, topology, seed)
  -> pcf_benchmark, driven by tools/run_benchmark.py
  -> results/raw/*.csv  (immutable; one row per repetition)
  -> tools/validate_raw_data.py, tools/aggregate_results.py
  -> results/processed/*.csv, results/processed/results_summary.json
  -> tools/emit_latex_tables.py
  -> results/tables/*.tex  (no number is hand-typed)
```

`tools/build_report.sh` runs this pipeline end to end for every official
campaign; `tools/package_release.sh` packages `instances/` and `results/`
into release assets.
