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
  hpac.cpp / dhpac.cpp         heap-based variant and its dual
  hpac_eager.cpp                hpac with an update-in-place std::set
                                 instead of a lazy-deletion heap
  hpac_bounded.cpp               hpac whose lazy heap is periodically
                                 rebuilt once past a size bound
  hipac.cpp / hopac.cpp          specialized heap variants (in-forests/out-forests)
  rac.cpp                      rake-and-compress / top-tree algorithm
  instance.cpp                 instance validation, canonicalization
  cli.cpp                      pcf_solve executable
  benchmark.cpp                 pcf_benchmark executable
  internal/work_graph.hpp      shared internal graph-contraction helper
tests/test_main.cpp           CTest suite (pcf_tests) — see docs/VALIDATION.md
third_party/bppf/             unmodified upstream Bounded-Precision
                               Parametric Pseudoflow source (independent
                               max-flow oracle and optional baseline)
tools/                        Python: instance generators, benchmark runner,
                               BPPF converter/verifier, aggregation/reporting
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
| `compute_hpac` | any forest | $O(n^2\log n)$ worst case, $O(n\log n)$ typical | $O(n)$ | heap-based |
| `compute_dhpac` | any forest | as `hpac` | $O(n)$ | dual of `hpac` |
| `compute_hipac` | in-forests only | $O(n\log n)$ | $O(n)$ | requires out-degree $\le 1$ |
| `compute_hopac` | out-forests only | $O(n\log n)$ | $O(n)$ | requires in-degree $\le 1$ |
| `compute_rac` | any tree | $O(n\log n)$ | $O(n\log n)$ | rake-and-compress / top-tree |
| `compute_hpac_eager` | any forest | as `hpac` | $O(n)$ (not just typical) | memory-bounded, see below |
| `compute_hpac_bounded` | any forest | as `hpac` (amortized) | $O(n)$ (not just typical) | memory-bounded, see below |

`HIPaC`/`HOPaC` assume their required orientation and do not validate it at
runtime; passing a mixed-orientation forest to either is a caller error, not
a checked precondition.

`hpac`'s lazy-deletion heap re-pushes one entry per incident edge every time
a node's closure sum changes without removing the stale one, which stays
$O(n)$ on typical inputs but can grow past it on a high-degree hub (the
`star-mixed` family). `compute_hpac_eager`/`compute_hpac_bounded` solve
exactly that case — `hpac_eager` via an update-in-place `std::set` (at most
one live entry per edge/node ever), `hpac_bounded` via periodic full
rebuilds of the same lazy heap once it outgrows a constant factor of the
live candidate count — both keeping `hpac`'s worst-case time bound. They are
not part of the main computational study reported in the paper (which uses
`hpac` throughout); reach for them directly whenever an input can have a
high-degree hub and `hpac`'s memory growth is a concern.

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
- `pcf_bppf_oracle` / `pcf_bppf`: the unmodified upstream BPPF binaries
  (`third_party/bppf/`), built with and without `-DBREAKPOINTS`
  respectively, invoked two different ways for two different questions
  (see README's "Two ways to compare against BPPF"): `pcf_bppf_oracle`
  alone, once per breakpoint with one exact lambda baked in per call, by
  `tools/verify_with_bppf.py` / `tools/run_bppf_campaign.py` (correctness);
  both binaries, once per instance with a whole probe sequence in BPPF's
  native affine encoding, by `tools/convert_to_bppf_sequence.py` /
  `tools/validate_bppf_sequence.py` / `tools/run_bppf_native_campaign.py`
  (native speed, `pcf_bppf_oracle` used only for the one-off agreement
  check outside the timed region, `pcf_bppf` for the actual timing).

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
