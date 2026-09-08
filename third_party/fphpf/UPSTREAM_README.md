# Fully parametric HPF (fetched from upstream, not redistributed)

Hochbaum's **fully parametric** pseudoflow minimum-cut solver: given only a
range for the parameter, it computes every breakpoint by itself. This is the
implementation the manuscript races against in the comparison of
Section "Comparison with parametric pseudoflow".

- **Upstream**: <https://github.com/hochbaumGroup/pseudoflow-parametric-cut-v2>
  ("Fully Parametric Cut HPF for Linear parameter functions, Version 2 --
  May 2025"), landing page
  <https://riot.ieor.berkeley.edu/Applications/full-para-HPF/pseudoflow-parametric-cut.html>.
- **Commit used** (pinned in `fetch.sh`): `fbd480fb1c4215792768b2a22f01d731a9fb6a27` (2025-05-27).
- **Not redistributed**: the solver's source is not committed here. Run
  `third_party/fphpf/fetch.sh`, which downloads the pinned commit from the
  authors' repository into `c/` and `core/` (the upstream layout, so that
  `hpf.c`'s `#include "../core/libhpf.h"` needs no change), copies their
  `LICENSE.md`, and applies the two format changes below, verifying each.
  Files used: `src/pseudoflow/c/hpf.c`, `src/pseudoflow/core/libhpf.c`,
  `src/pseudoflow/core/libhpf.h`. The Python and Matlab wrappers are not
  built. `c/`, `core/` and `LICENSE.md` are git-ignored.
- **Method**: a variant of the fully parametric HPF algorithm of
  DS Hochbaum (2008), *The Pseudoflow algorithm: a new algorithm for the
  maximum flow problem*, Operations Research 58(4):992-1009 -- the same
  reference the manuscript cites as the state of the art for arbitrary
  precedence graphs.
- **License**: UC Berkeley research licence, fetched together with the
  source (`LICENSE.md`, git-ignored). Created by Quico Spaen and Dorit S.
  Hochbaum, modified by Ayleen Irribarra.

## Local modifications

`local.patch` is the exact diff against the upstream commit above (applied by
`fetch.sh` as two explicit substitutions, each verified). It touches
**two `printf` format strings and nothing else** -- no algorithm, no data
structure, no control flow:

1. `hpf.c`, timing line: `"t %.3lf %.3lf %.3lf"` -> `"t %.9lf %.9lf %.9lf"`.
   Upstream prints the read/initialize/solve times with millisecond
   granularity, which is too coarse to time instances that solve in a few
   milliseconds. Only the printed precision changes; the timers themselves
   are upstream's.
2. `hpf.c`, per-group parameter line: `"l %lf "` -> `"l %.17g "`.
   Upstream prints the parameter with `%lf`'s default six decimals. The
   grouping of nodes is done in C on the exact `double` (`clam != clambda`),
   so this is a printing limit only -- but at six decimals two groups whose
   parameters differ by less than 1e-6 print identically and are
   indistinguishable downstream, which looks exactly like the solver having
   merged two closure layers when it has not. Verified on
   `gen_n10000_rho0.9_independent-signed_seed0`: at six decimals the parsed
   partition had 5413 layers against HPaC's 5414; at 17 significant digits
   both have 5414.

Reproduce with `fetch.sh`; the result is byte-identical to the sources the
measurements of campaign H were made with.

## Reading the output (important)

The v2 C output **does not follow its own README**. The README documents one
`n <node-id> <breakpoint>` line per node; `hpf.c`'s `writeOutput` instead
sorts nodes by their `cuts` value and emits one line per distinct value,

    l <parameter> <node-id> <node-id> ...

grouping every node sharing that value (the README's `l` line of interval
bounds is commented out in the source).

Furthermore, `libhpf.c`'s `addBreakpoint` sets a node's entry to the
parameter of the *first breakpoint at which the node is already in the source
set* -- that is, the **upper** bound of the first interval containing the
node, not the parameter at which it enters. Grouping by that value therefore
reproduces the closure layers and their order correctly, but labels each
group with the *next* group's parameter and pushes the final group onto the
`LAMBDA_HIGH` sentinel. `tools/race_fphpf.py` consequently takes only the
**partition** from this solver and recomputes every breakpoint exactly, as
`lambda_r = P(I_r)/W(I_r)`, so no floating-point value produced here enters
the comparison.

## Fixed absolute tolerance in parameter space

`libhpf.c` declares `static double TOL = 1E-7;` (commented "tolerance for
denominator == 0") and, when it recurses on the intersection of two linear
pieces, brackets the search with `lambdaIntersect - TOL` and
`lambdaIntersect + TOL` ("Add/subtract TOL to prevent numerical issues"). Two
breakpoints closer together than about `2*TOL = 2e-7` therefore cannot both
be found: the corresponding closure layers come out merged.

This is a property of the implementation, not of double precision -- the two
thresholds involved are perfectly distinct as doubles. Verified on
`gen_n10000_rho0.9_correlated_seed0`: HPaC's layers 1421 and 1422 have exact
ratios 2299/2226 and 2362/2287, whose gap is 1/5090862 = 1.96e-7; the solver
returns their union as a single group. Over the 2,400 mixed-forest instances
with n <= 1000 the smallest gap between consecutive breakpoints is 2.21e-7,
just above the threshold, and no merge occurs; from n = 10^4 on, where
breakpoints are denser, merges appear and become systematic (see
`results/raw/campaign_h_*`). `tools/race_fphpf.py` reports them per instance
as `same_partition = False`; they are never silently accepted.

## Caveat stated by the upstream authors

Both v1 and v2 of the README state:

> This implementation does not use *free runs* nor does it use warm starts
> with information from previous runs (see pg.15). This implementation should
> therefore **not be used** for comparison with the fully parametric HPF
> algorithm.

This is reported in the manuscript alongside the measurements: the numbers
here characterise this public implementation, not a lower bound on what the
fully parametric HPF method could achieve.

## How this solver is used here

`tools/convert_to_fphpf.py` writes one input file per instance and
`tools/race_fphpf.py` runs the race; `docs/EXPERIMENTAL_PROTOCOL.md`
(campaign H) states the sweep, and the report's "Comparison with the fully
parametric pseudoflow solver" states the protocol in full. In short:

- **Input.** The instance is encoded through the standard
  maximum-closure/minimum-cut reduction, with source- and sink-adjacent
  capacities affine in the parameter. Because the solver requires
  source-adjacent capacities to be non-decreasing in its parameter while the
  manuscript's vertex value `p_i - lambda*w_i` decreases in lambda, the
  solver is run on `mu = -lambda`: `source->i` gets `(const, mult) =
  (p_i, w_i)`, `i->sink` gets `(-p_i, -w_i)`, and each precedence arc gets a
  large constant capacity with zero multiplier. The parameter range is
  `[-max|p_i|-1, +max|p_i|+1]`, which brackets every vertex ratio because
  `w_i >= 1`, and is derived from the instance alone.
- **What is given to it.** The instance and that range, and nothing else. In
  particular no threshold, probe or breakpoint computed by any algorithm of
  this repository ever reaches it: the solver locates all breakpoints itself.
- **What is taken from it.** Only the partition of the vertices into closure
  layers. Every breakpoint is then recomputed here in exact rational
  arithmetic as `lambda_r = P(I_r)/W(I_r)`, so no floating-point value it
  produces enters any reported number.
- **What is timed.** Its own internal solve timer (the third field of the `t`
  line, input parsing and process start-up excluded), against `hpac`'s
  in-process time for the full parametric sweep on the same instance, both as
  medians of 11 repetitions run in the same session.
- **Role.** Competitor in a timed race, never a correctness oracle. The
  algorithms of this repository are validated independently
  (`docs/VALIDATION.md`).

Reproduce the whole campaign with:

```bash
third_party/fphpf/fetch.sh          # downloads the solver from its authors' repo
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --target pcf_fphpf
python3 tools/race_fphpf.py --pcf-solve build/pcf_solve \
  --pcf-benchmark build/pcf_benchmark --hpf build/pcf_fphpf \
  --instances instances/campaign_b --repetitions 11 \
  --output results/raw/campaign_h_fphpf_mixed_n100-1000.csv
```

## Relationship to the simple-parametric solver

Not to be confused with
<https://github.com/hochbaumGroup/Bounded-precision-simple-parametric>, the
*simple* parametric solver, which only evaluates minimum cuts at parameter
values supplied by the caller and therefore cannot compute the parametric
solution on its own. Every earlier version of this study used that solver as
its baseline, which forced the comparison to hand it the `k+1` probe values
bracketing `hpac`'s own exact thresholds. That protocol was withdrawn on
2026-09-08 together with `third_party/bppf/`, the tools
`convert_to_bppf_sequence.py` and `run_bppf_native_campaign.py`, the CMake
targets `pcf_bppf`/`pcf_bppf_oracle` and campaign G's data; all of it remains
in git history at tag `v0.3.0`.
