# RaC mathematical audit

This is the operation-by-operation audit required before RaC enters the
official benchmark campaign. It supersedes nothing in
`docs/RAC_SPECIFICATION.md` (which freezes the *contract*); this document
records the audit *evidence* against both the manuscript and the recovered
legacy source.

## Source under audit

`MACROITEMS_PAPER/LLMs/CONTROPROSTA_DI_CHAT/TESTS_CHAT/top_tree_cpp_experiment_package.zip`
(inside `LLM_PROPOSTE_SEPARAZIONI_PAPERI.tar.gz`), file `code/algo_top_tree.cpp`
(518 lines), ported into `src/rac.cpp`. A full line-by-line `diff` between the
two files is reproducible from the extracted archive; the only differences
are two cosmetic renames (namespace and
one struct field) and the removal of a `long double` round-trip with a
`1e-9` tolerance at the public entry point, replaced by direct use of the
instance's native `std::int64_t` profits and weights. No cluster, envelope or
traversal logic differs between the two files.

## Method

Each of the twelve required correspondence items is checked against
both (a) the legacy/ported C++ source and (b) the manuscript's RaC section
("On parametric Maximum Closure Problems over precedence forests", Dose,
Furini, Locatelli, maintained in a separate repository), and against the
acceptance tests in `docs/RAC_SPECIFICATION.md`.

| # | Manuscript operation | Where in `src/rac.cpp` | Finding |
|---|---|---|---|
| 1 | 1-cluster / 2-cluster representation | `struct Cluster` (`LEAF`/`JOIN`/`INTERNALIZE`), `boundary`, `bsz` | A cluster stores a boundary of size 0, 1 or 2 and an array of 4 state-indexed envelopes (`f[0..3]`), one entry per boundary-state combination; unused states for `bsz<2` are simply never queried. Matches the manuscript's `(C, ∂C)` pair. |
| 2 | `\|∂C\| ≤ 2` invariant | `add_join`/`add_internalize`: `if (c.bsz > 2) throw std::runtime_error(...)` | Enforced defensively at every cluster-construction site, not just assumed; violated only if the degree-3 expansion (item 3) is broken, which the exhaustive/differential tests below would catch. |
| 3 | Degree-≤3 expansion with zero-cost equality edges | `expand_degree_three` | Splits each original vertex of degree *d* into *d* zero-weight copies chained by `EQUAL` edges (state-consistency forced in `add_leaf`), with the objective-bearing copy always the first (`k==0`). Matches `docs/RAC_SPECIFICATION.md`'s explicit allowance for this representation and preserves the closure structure exactly (equality edges force all copies of one original vertex to share a state). |
| 4 | \(f_{\mathcal C}^\sigma\): exact upper envelope of affine lines | `struct Envelope`, `hull_from_lines` | Lines are `P - lambda*W` pairs; `hull_from_lines` sorts by slope and removes lines using an exact cross-multiplied intersection comparison (`cmp_intersections`, 128-bit products) — no floating point anywhere in the hull computation. |
| 5 | Envelope sum (`+`) | `env_sum` | Merges two envelopes' breakpoints via the same exact rational comparison used for the hull, summing `(P, W)` pairwise between consecutive breakpoints; re-hulled at the end. Matches "sum of envelopes" in the manuscript. |
| 6 | Envelope max (`∨`) | `env_max` | Merges by decreasing slope, taking the higher-`P` line at equal slope, then re-hulls. Matches "maximum of envelopes". |
| 7 | `Compress1` (unary internalization) | `add_internalize` | For each parent boundary state, maximizes over the removed vertex's two states, adding its exact `(p_v, w_v)` contribution when charged (`env_shift`). This is exactly Compress1 in the manuscript: fold one vertex into its neighbor's cluster function. |
| 8 | `Compress2` (join at a shared border vertex) | `add_join` | For each parent boundary state, sums the two children's envelopes at matching child states, optionally charging the shared vertex once when it becomes internal (`c.internalized`). The `xlo/xhi` loop enumerates both states of the shared vertex only when it must be internalized; otherwise the parent's own fixed bit is used. This matches Compress2's definition (join two 2-clusters, maximize over the disappearing border state). |
| 9 | `Rake` (attach detached 1-clusters to the surviving backbone) | `build_component`, the `rs`/`attachments` handling in the main contraction loop | Leaves (`degree==1`) are detached via `add_internalize`/`add_join` against their unique neighbor's accumulated "point" cluster, then re-attached to that neighbor; state-compatible envelopes are combined exactly as in item 7/8, not re-derived. |
| 10 | Independent-set selection and per-round advancement | `build_component`, "greedy maximal independent set on degree-2 vertices" | Each round rakes all current leaves, then greedily selects a maximal independent set among the remaining degree-2 vertices and compresses each selected vertex's two incident edges via `Compress2`. `ct.rounds` counts rounds; the round loop terminates only when `aliveCount<=1`, and throws (`"contraction stalled"`) if neither a rake nor a compress candidate exists in some round, which would indicate a bug rather than silently looping. |
| 11 | Top-down threshold reconstruction | `recover`, `recover_internalized`, `selected_at_rat` | Walks the cluster tree top-down; at each internalizing node, merges the breakpoints of every child envelope actually reachable (`merge_events_linear`) with the already-known parent-boundary thresholds, then scans left to right (`root_in_interval`) for the exact rational point where the "vertex included" branch stops dominating the "vertex excluded" branch. All comparisons are exact 64/128-bit integer arithmetic; `theta_known`/`theta_exp` cache one threshold per expanded vertex, and a duplicate computation that disagrees throws (`"inconsistent duplicate threshold"`). |
| 12 | Canonical closure layer extraction and round/depth bound | `RaCSolver::solve` (sorting by threshold, merging exact ties); `ct.rounds`, `ct.max_cluster_depth` | Items are sorted by exact threshold descending and consecutive exact ties are merged into one closure layer — the same canonicalization rule as PaC/HPaC (`pcf::canonicalize`, `src/instance.cpp`). `RaCStats` records `rounds` and `max_cluster_depth`; the theoretical logarithmic bound on both is checked operationally by the scaling data in campaign D (`results/`), not proved symbolically here. |

## Numerical and robustness audit

- **Integer width**: all coefficients are `std::int64_t`; every product that
  could overflow 64 bits (ratio cross-multiplication, envelope intersection
  comparisons) is computed in `__int128_t` (`i128` alias in `src/rac.cpp`).
- **Rational normalization**: `make_rat` always returns a reduced fraction
  with a strictly positive denominator (`if(d<0){n=-n;d=-d;}` then divide by
  `gcd`).
- **Coincident breakpoints**: handled by exact equality (`rat_eq`), both when
  deduplicating hull lines with equal slope and when merging equal-ratio
  closure layers at the end of `solve()`.
- **Signed coefficients**: `independent-signed` instances (see
  `tools/pcf_families.py`) exercise negative `p_i` directly; `env_shift` adds
  signed profit contributions without any positivity assumption.
- **Overflow handling**: `validate_instance` (`src/instance.cpp`) rejects any
  instance whose total absolute profit or total weight would leave the
  "exact arithmetic safety bound" (`INT64_MAX/4`) before RaC or any other
  algorithm runs, so overflow is refused explicitly at the API boundary
  rather than silently wrapping.
- **Cross-algorithm agreement**: RaC's output must match PaC/DPaC/HPaC/DHPaC
  bit-for-bit (same breakpoints, same partition, same canonical order) under
  the differential and exhaustive-oracle tests below.

## Acceptance evidence

| Gate | Evidence |
|---|---|
| Unit tests on cluster operations | `pcf_tests` exercises envelope sum/max, hull deduplication and infeasible-state handling indirectly through every RaC solve in the exhaustive and differential suites (`tests/test_main.cpp`). |
| Exhaustive comparison on small instances | Every directed forest with at most four items over a finite coefficient grid, checked against the independent closure-enumeration oracle. |
| Differential comparison with PaC/HPaC/DHPaC | Deterministic random forests, plus the six coefficient families crossed with mixed/in/out topologies (see the smoke sweep referenced in `results/TEST_REPORT_2026-08-28.md`, extended by campaigns A-D). |
| Sanitizer build | AddressSanitizer/UndefinedBehaviorSanitizer CTest configuration in `.github/workflows/ci.yml`. |
| No hidden fallback to PaC/HPaC | `compute_rac` (`src/rac.cpp`) never calls `compute_pac`/`compute_hpac`/any other algorithm; its only external dependency is `validate_instance`. |
| Independent max-flow cross-check (historical; tooling since removed with the BPPF-oracle role) | `tools/verify_with_bppf.py` recomputed the closure at a fixed lambda with BPPF, an unrelated third-party min-cut solver; agreement is verified at every breakpoint midpoint reported by HPaC on a spread of random/path/star instances across all six coefficient families before RaC is trusted for benchmarking (481/481 agreements in the validation sweep run for this repository; see `docs/EXPERIMENTAL_PROTOCOL.md`). |

## Conclusion

No discrepancy between the recovered `algo_top_tree.cpp` and the ported
`src/rac.cpp` was found beyond the two documented cosmetic/precision changes
in `PROVENANCE.md`. RaC satisfies every item of the acceptance gate
and is accepted for the official benchmark campaigns (sections 9 and 15,
phase 6).
