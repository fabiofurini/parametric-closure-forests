# Experimental Plan V3 — clean redo of the computational study

**Status: DRAFT under joint validation (FF + coauthors). Becomes the
preregistered plan once validated; no campaign starts before that.**

This plan supersedes every benchmark result produced before 2026-08-31. All
prior raw/processed results were moved to the untracked local folder
`_OLD_RUNS_ARCHIVE_20260831/` (kept only for reference during the redo,
deleted after release v0.3.0). No number produced before the freeze commit
of Phase 0 may be cited in the manuscript, the technical report, or any
table under `results/`.

Deviations, if any become necessary, are recorded in the "Deviations"
section at the bottom before the affected campaign is (re)run.

---

## 0. Decisions log (2026-08-31, recorded by FF)

1. **Full clean rerun.** All campaigns rerun from scratch from one frozen
   commit, on one machine, in one sweep. No mixing of raw CSVs across
   commits or dates.
2. **BPPF comparison = the v1-style comparison, restored.** The two
   algorithms are compared **on the same problem**: BPPF runs its own
   native parametric sweep (it receives only the instance and finds all
   breakpoints itself, bounded precision, `prec = 1e-6` as in v1), one
   process per instance, against HPaC's single in-process sweep. The
   current per-breakpoint measurement — where BPPF is *handed* HPaC's
   breakpoints — is removed from the paper as a comparison (it is a
   useless speed test by construction); it survives only as an internal
   correctness oracle in the validation layer (`docs/VALIDATION.md`).
3. **BPPF precision issues get at most a comment.** Where BPPF's
   fixed-point arithmetic merges close breakpoints / misses the optimal
   layer split on some instances, the paper reports it v1-style: a short
   factual comment with the instance count (v1: 8/2,400), nothing more.
4. **Table-8 memory problem: diagnosed, root-caused, and eliminated at the
   source** (diagnostic of 2026-08-31, recorded below in §2bis). The
   O(n)-space theorem is about the algorithm; the ">8 GB" rows were an
   artifact of the lazy-deletion heap in `hpac.cpp` (each hub touch
   re-pushes one entry per incident arc without deleting stale ones →
   Θ(n²) heap entries on stars; measured: RSS ×100 for n ×10).
   **Decision: the bounded-rebuild heap becomes the official HPaC
   implementation** — measured *faster* than the lazy heap everywhere
   (~2× on large random forests/trees, ~4× on stars) with identical
   output hashes and genuinely O(n) memory. The same rebuild policy is
   applied to the dual **DHPaC**. The lazy implementation stays in the
   repo as `hpac_lazy` (internal reference; one concise red sentence in
   the paper explains the heap policy next to the O(n)-space statement).
   The rebuilt star table reports **PaC (full size range — cheap on
   stars, ~70 s at n=100k), HPaC (=bounded, n ≤ 20,000 by preregistered
   cutoff), RaC (full range)**. HPaC-Eager is dropped from the paper
   (kept in repo); DHPaC dropped from this table.
5bis. **No pass may burn hours in pure timeouts.** Where a slower
   algorithm's asymptotic trend is already established by the smaller
   sizes, a preregistered size cutoff applies instead of running into the
   300 s cap size after size: PaC/DPaC on random forests n ≤ 20,000 (as
   before), **HPaC/DHPaC on stars n ≤ 20,000** (trend n² established:
   ~6.4 s at 10k, ~26 s at 20k, vs RaC's 0.06 s). Cutoffs are stated in
   the protocol and in the table captions.
5. **Star heap-variant runs use the same caps as everything else**
   (300 s wall-clock, 8 GiB memory). No extended-timeout pass.
6. **Campaign C aggregated per density** in addition to per size; the
   suspected RaC/HPaC crossover at ρ=1.0 (trees) gets a dedicated sentence
   iff confirmed by the new sweep, otherwise the per-density range is
   reported and the open note is closed anyway.
7. **Manuscript restructuring:** current §4.2.1 ("Structured forests and
   the star counterexample") is dissolved into the end of §4.2 as a
   *focus on particular instance classes* (paths, binary trees, stars) —
   not a separate subsection.
8. **Timeline: one night.** The whole sweep runs tonight (2026-08-31 →
   2026-09-01), parallelized across pinned cores (§4bis); tomorrow morning
   the computational section of the paper must be ready, the results
   organized under `results/`, and GitHub aligned (all commits pushed,
   release cut).
9. **Manuscript style rules** (Phase 4, binding for the rewrite):
   - every new or changed sentence goes in red (`\rev{...}`);
   - the computational section is **a few pages at most**: the paper
     targets Mathematical Programming / Algorithmica, so §4 is *support
     for the theory*, not a standalone experimental study — details live
     in the technical report and this repo's docs;
   - every conclusion is backed by the data of this sweep and explicitly
     scoped to the tested instance classes ("on the mixed-forest
     instances of campaign C…", never in general);
   - **no general dominance claims**: never "algorithm X dominates/
     outperforms Y" unqualified — always "faster on ⟨these topologies,
     these sizes, these families⟩", with the opposite cases stated
     (e.g. stars) where they exist;
   - preferred phrasing: *"on these instances we observed that …"*, and
     wherever possible each observation comes with the **intuition for
     the mechanism** behind it (one sentence: e.g. the hub-touch/lazy-heap
     mechanism on stars, the wing collapse to singletons on in-/out-trees,
     the O(log n) contraction rounds of RaC).
10. **Cleanup executed:** old runs (`results/raw|processed|tables|logs`,
    `pilot_exploratory`, `TEST_REPORT_2026-08-28.md`, `dist/*.zip`), old
    pilot/probe instance dirs (`in_large_pilot`, `out_large_pilot`,
    `random_*`, `structured`), the obsolete `docs/TODO_DIAG.md` (fully
    superseded by this plan) and the obsolete technical report
    (`report/*` — its numbers predate the freeze; it is rewritten from
    the new sweep in Phase 4) are parked in `_OLD_RUNS_ARCHIVE_20260831/`,
    to be deleted at Phase 5.

---

## 1. Reproducibility contract

Binding for every campaign below:

1. **One frozen commit.** Phase 0 produces a tagged commit; `pcf_benchmark`
   embeds the hash in every raw CSV row. At QA time (Phase 3), every row in
   `results/raw/*.csv` must carry that same hash, or the sweep is invalid.
2. **One machine, one sweep.** Same machine as recorded in
   `docs/EXPERIMENTAL_PROTOCOL.md` (i7-12700, 32 GiB, Ubuntu 22.04.5,
   GCC 11.4.0 `-O3`), single-threaded, `taskset`-pinned; `powersave`
   governor limitation stays documented; all headline numbers are paired
   same-instance ratios (median + IQR).
3. **Instances only from seeded generators**, manifested and verified
   (`build_instance_manifest.py --verify`) before any benchmark reads them.
   No `.pcf` file is ever hand-edited.
4. **No hand-typed number.** raw CSV → `validate_raw_data.py` →
   `aggregate_results.py` → `emit_latex_tables.py` → `results/tables/*.tex`
   → `\input` in report/paper.
5. **Uniform caps.** 300 s timeout and 8 GiB ceiling (`ulimit -v`) for
   every run of every campaign. Censored runs recorded in
   `*.failures.csv` and reported, never imputed.
6. **Statistics.** Median + IQR of the per-instance paired ratio; never a
   ratio of aggregate means.
7. **Zero-mismatch gate** among our own algorithms:
   `results/processed/mismatches.csv` must be empty. (BPPF is *expected*
   to show bounded-precision deviations on some instances; those are
   counted and commented, not treated as mismatches of ours.)
8. **Release v0.3.0** with `instances.zip`, `results.zip`, SHA-256
   checksums; the clean-clone checklist of `docs/REPRODUCIBILITY.md`
   must pass.

---

## 2. Phase 0 — Engineering + freeze (before any run)

Code work needed by the new decisions, then freeze:

- [ ] **T1 — BPPF autonomous-sweep driver (v1-style).** Adapt the native
      pipeline so that the *timed* BPPF run receives **only the instance**
      (affine two-number capacities + a λ interval, `p interval` header)
      and discovers every breakpoint itself, exactly like the v1
      methodology — never HPaC's breakpoint list. **De-risked:** upstream
      `pseudopar.c` supports `lambda_format INTERVAL` natively, and the
      exact v1 driver exists as reference
      (`MACROITEMS/CODE_PARAMETRIC_PSEUDOFLOW/scripts/hpf_compare.py` +
      `hpf_medium_batch.py`, output `runs_bppf_and_hfma_medium.csv`):
      port its conversion/interval/precision choices verbatim into
      `tools/run_bppf_native_campaign.py` (reworked), with a module
      docstring stating the equal-problem guarantee.
- [ ] **T2 — BPPF agreement checker (tolerance-aware).** Post-run,
      untimed: compare BPPF's returned breakpoints/closures against
      HPaC's, classifying every deviation as (a) tolerance merge
      (< 10^-prec gap) or (b) genuine disagreement. Genuine disagreement
      on any instance stops the campaign (it would mean our encoding is
      wrong). Output: per-instance flags feeding the paper's one-comment
      count.
- [x] **T3 — Star memory diagnostic. DONE 2026-08-31 (see §2bis).**
      Root cause confirmed in code and measurement; led to decision #4.
- [ ] **T5 — Bounded heap becomes official.** (i) Wire `pcf_benchmark`/
      `pcf_solve` so that `hpac` runs the bounded-rebuild implementation
      and the lazy one stays available as `hpac_lazy` (internal
      reference); (ii) apply the same rebuild policy to `dhpac`
      (mirror change); (iii) extend the differential tests: bounded-HPaC
      and bounded-DHPaC vs `hpac_lazy` and the enumeration oracle on the
      exhaustive/random suites. All green before the freeze.
- [ ] **T4 — Per-density aggregation** for campaign C in
      `aggregate_results.py`/`emit_latex_tables.py` (group by ρ as well
      as n), producing the crossover table for decision #6.
- [ ] Commit all pending work (campaign-E full-matrix script + guard,
      `test_hipac_against_hpac`, doc edits, removal of superseded
      campaign-E CSVs, T1–T4, this plan).
- [ ] `ctest` passes on Release **and** ASan/UBSan Debug; fresh
      `results/TEST_REPORT_<date>.md`.
- [ ] Tag `campaign-freeze-v3`, push; record environment snapshot in
      `results/logs/`.

## 2bis. Table-8 diagnostic record (2026-08-31, closes the "what happened" question)

Purpose of every campaign, restated: **establish the growth trend and the
paired ratios** — nothing needs exhaustive absolute coverage beyond that.

Mechanism (code): `touch_edge` in `src/hpac.cpp` pushes a fresh heap entry
at every closure-sum change without deleting the stale one (lazy deletion,
version counters). On a star every peel/contract touches the hub, and each
hub touch re-pushes one entry per incident arc (~n): ~n events × ~n pushes
= Θ(n²) heap entries. The `priority_queue`'s backing vector also doubles
during growth (transient 2×), which is why the 8 GiB cap already falls at
n = 20,000.

Measurements (star, seed 0, `independent-positive`, 1 rep, Release build):

| n | PaC | HPaC-lazy | HPaC-Eager | HPaC-Bounded | RaC |
|---|---|---|---|---|---|
| 1,000 | 15 ms / 3.3 MiB | 139 ms / 15.6 MiB | 104 ms / 3.4 MiB | 64 ms / 3.9 MiB | 17 ms / 5.6 MiB |
| 10,000 | 680 ms / 5.6 MiB | 27.0 s / **1,541 MiB** | 13.3 s / 6.4 MiB | 6.4 s / 8.2 MiB | 57 ms / 23.4 MiB |

Lazy RSS ×100 for n ×10 → quadratic; all other implementations flat/linear.
The theorem's O(n) space is about the algorithm (PaC: 5.6 MiB at n=10⁴);
the blow-up was purely the lazy-heap implementation.

Bonus finding (drives decision #4): on large *random* forests the bounded
heap is also ~2× **faster** than the lazy one (e.g. n=100k, ρ=1.0, five
coefficient families: 330–390 ms vs 690–950 ms, RSS 42 vs 105–114 MiB),
with identical output hashes on every instance tested.

## 3. Phase 1 — Instances

Regenerate or complete every instance directory (generators are
deterministic; existing directories are verified rather than regenerated).

| Directory | Contents | Count |
|---|---|---|
| `instances/campaign_b` | mixed, n=100..1000, ρ∈{.3,.6,.9,1}, 6 families, 10 seeds | 2,400 |
| `instances/campaign_c` | mixed, n=10k..100k, same matrix | 2,400 |
| `instances/campaign_c_n{10000,20000}_subset` | symlinks into campaign_c | 240 each |
| `instances/campaign_d_{path,binary,star}` | structured, 10 sizes, 10 seeds, 6 families | 600 each |
| `instances/campaign_d_{shape}_pac_subset` | symlinks, n ≤ 2,000 | 300 each |
| `instances/campaign_d_star_large_only` | symlinks, n ∈ {20k, 50k, 100k} | 180 |
| `instances/campaign_e_{in,out}` | in/out, 20 sizes, ρ∈{.3,.6,.9,1}, 10 seeds | 4,800 each |
| `instances/campaign_f` | BPPF validation subset (n∈{100,200,500,1000}, ρ=0.6, 3 seeds) | 72 |

- [ ] Complete `campaign_e_in` (currently 4,699/4,800; generator is
      idempotent) and generate `campaign_e_out`.
- [ ] Manifest build + `--verify` for every directory; any mismatch stops
      the plan here.

## 4. Phase 2 — Campaigns

Drivers: `tools/run_official_campaigns.sh` (core 0) and
`tools/run_dual_variant_campaigns.sh` (core 1, concurrent — single-threaded
processes pinned to different physical cores). Campaign G has its own
driver (T1). Every launch logged under `results/logs/` with a dated name.

| Camp. | Instances | Algorithms (reps) | Shuffle seed | Feeds (paper v3) |
|---|---|---|---|---|
| **A** | exhaustive/small (`pcf_tests`, Phase 0) | all, vs. enumeration oracle | — | correctness statement, §4 intro |
| **B** | campaign_b (2,400) | pac,hpac,rac (11); dpac,dhpac (11) | 1; 5 | Fig. 5 (medium-range PaC/HPaC/DPaC/DHPaC) |
| **C** | campaign_c (2,400) | hpac,rac (3); dhpac (3); pac n=10k (2) / n=20k (3); dpac idem | 2; 6 | Fig. 6; **per-density RaC/HPaC table + ρ=1.0 crossover check** |
| **D** | campaign_d path/binary/star (600 each) | path/binary: hpac,rac (3), dhpac (3), pac,dpac n≤2,000 (3); **star:** rac full range (3), hpac,dhpac n≤20,000 (3, cutoff 5bis), **pac full range (3)** | 3; 7 | end of §4.2 (instance-classes focus): path/binary ratios; **rebuilt star table = PaC / HPaC / RaC** (decision #4); trend + ratios only |
| **E** | campaign_e_in / _out (4,800 each) | hpac,hipac,rac / hpac,hopac,rac (3); dhpac (3) | 4; 8 | §4.3 (HIPaC/HOPaC ratios, full v1-aligned matrix) |
| **F** | campaign_f (72) | per-breakpoint exact BPPF oracle (validation ONLY — produces no paper number) | — | `docs/VALIDATION.md` layer 2; gate for G's encoding |
| **G** | campaign_b (2,400) | **BPPF native autonomous sweep (v1-style)** vs hpac, 5 reps, `prec=1e-6` | — | §4.4 (the restored v1 comparison) + Conclusion claim |

Campaign G rules (the restored v1 comparison):

- **Equal problem:** both solvers compute the *full parametric solution*
  of the same instance. HPaC: one in-process call. BPPF: one process,
  autonomous sweep, no breakpoint list supplied (T1). Timed regions
  exclude conversion and I/O for both.
- **Gate before timing:** T2 agreement check on the campaign-F subset
  must classify every deviation as a tolerance artifact
  (`genuine_mismatches = 0`); one genuine mismatch stops the campaign.
- **Precision/scope accounting:** instances where BPPF (fixed-point,
  `prec=1e-6`) merges close breakpoints or where the encoding's 2^53
  representation guard rejects the instance are counted per size/family
  and reported in one short comment, v1-style ("on X of 2,400 instances
  BPPF does not recover the exact optimal layer sequence, due to its
  bounded-precision arithmetic"), never silently dropped.
- **Reported:** median + IQR paired ratio (BPPF/HPaC) per size; the
  Conclusion claim is restated from these numbers.

## 4bis. One-night schedule (2026-08-31 evening → 2026-09-01 morning)

Campaigns are independent per (instance-dir, algorithm-list) pass, each
single-threaded: they run **in parallel on distinct pinned P-cores**
(memory is not a constraint: at most two 8-GiB-capped star passes plus
small-footprint passes, on a 32 GiB machine). Assignment:

| Core | Passes (in order) | Est. |
|---|---|---|
| 0 | B official (pac,hpac,rac) → C official (hpac,rac + pac subsets) | ~5 h |
| 1 | B duals → C duals (dhpac, dpac subsets) → E duals (dhpac in+out) | ~7 h |
| 2 | D path + D binary (all passes) → F (validation) → **G** (after T2 gate) | ~5 h |
| 3 | D star: rac full; hpac,dhpac n≤20k; **pac full range** | ~3 h |
| 4 | E in (hpac,hipac,rac) | ~6 h |
| 5 | E out (hpac,hopac,rac) | ~6 h |

With the preregistered cutoffs (5bis) no pass burns hours in timeouts;
the critical path is campaign E (~6 h) / core 1 (~7 h). A small
orchestrator (`tools/run_night_sweep.sh`, part of Phase 0) encodes this
table so the whole night is one command; every pass logs to
`results/logs/`. HPaC everywhere means the bounded-heap implementation
(decision #4).

**Tomorrow-morning checklist (Phase 3–5 compressed):**
- [ ] verify completion per core log; record any censored/failed pass;
- [ ] Phase 3 pipeline + QA gates; regenerate all tables;
- [ ] rewrite manuscript §4 (few pages, red, concise, scoped claims with
      mechanism intuitions — decision #9) + report + repo docs;
- [ ] commit everything, push, tag, cut release v0.3.0 → GitHub aligned;
- [ ] results organized: `results/raw|processed|tables|logs` only, no
      stray files; `_OLD_RUNS_ARCHIVE_20260831/` ready for deletion.

## 5. Phase 3 — Aggregation and QA gates

```
python3 tools/validate_raw_data.py --raw results/raw/campaign_*.csv --instances-root .
python3 tools/aggregate_results.py  --raw results/raw/campaign_*.csv --output-dir results/processed
tools/build_report.sh
```

Gates (all must pass before anything reaches the paper):

- [ ] every raw row carries the freeze commit hash;
- [ ] `mismatches.csv` empty (our algorithms); BPPF deviations all
      classified by T2 as tolerance artifacts;
- [ ] every censored run (star OOM/timeout, G skips) appears in a
      failures/skip log and is accounted for in the text;
- [ ] T3 diagnostic confirms flat memory for Eager/Bounded on stars;
- [ ] new tables generated: per-density campaign-C ratios; rebuilt star
      table (5 columns, decision #4); campaign-G ratio table per size.

## 6. Phase 4 — Documents to update (in this order)

**Repo docs:**
- [ ] `docs/EXPERIMENTAL_PROTOCOL.md`: campaign G (autonomous sweep),
      star heap-variant pass, campaign F demoted to validation-only,
      uniform-caps decision; drop stale text.
- [ ] `docs/VALIDATION.md`, `README.md`: new totals; remove the
      "still pending" sentence; describe the two BPPF uses as
      validation-vs-comparison (comparison = autonomous sweep only).
- [ ] `report/computational_report.tex`: regenerate all numbers; delete
      red draft notes; replace the per-breakpoint §BPPF with the v1-style
      native comparison; fold the structured subsection per decision #7's
      logic; median/IQR wording throughout.

**Manuscript v3** (`PAPER_MARCO/v3/macroitems_v3_with_appendix.tex` —
every edit in `\rev{...}`/red, per the project's red-marking rule):
- [ ] Fig. 5, Fig. 6, Fig. 8: regenerate from the new sweep.
- [ ] §4.2: merge §4.2.1 into §4.2 as the closing *focus on particular
      instance classes*; rebuilt star table (PaC / HPaC-lazy /
      HPaC-Eager / HPaC-Bounded / RaC); add the one-paragraph lazy-heap
      explanation next to the O(n)-space statement (closes the apparent
      contradiction between the space theorem and the old ">8 GB" rows).
- [ ] §4.2: per-density sentence for the ρ=1.0 crossover (or per-density
      range if not confirmed).
- [ ] §4.4: **replace entirely** with the restored v1-style comparison
      (campaign G): CPU-time table+plot HPaC vs native BPPF sweep, plus
      the single precision comment (decision #3). The per-breakpoint
      framing and its 502–670× numbers are deleted from the paper.
- [ ] Conclusion: restate the BPPF sentence from campaign G's actual
      numbers (scoped to forests, as v1 did).
- [ ] Align wording where the paper says "mean" but the pipeline reports
      medians (Fig. 5/6 captions, §4.1–4.2 text).
- [ ] "Code and Data Availability": release v0.3.0 + new commit hash.
- [ ] **Instance-description appendix aligned** (`app:instance_generation`):
      the "Campaigns" paragraph must match this plan exactly — campaign E
      full 4×10 matrix; star cutoffs (HPaC/DHPaC n ≤ 20,000; PaC full
      range on stars); PaC/DPaC random subsets at n ∈ {10k, 20k}; the
      BPPF campaign described as the native autonomous sweep on the full
      2,400-instance medium bed (drop the per-breakpoint description and
      its 72-instance scoping rationale). Topologies and coefficient
      families are unchanged; only the campaign usage text moves.
- [ ] Delete the `\Fabio{}` boxes closed by the above.

**Out of scope of the campaigns** (tracked, needs Marco): Θ(n log n)
formulation and Ω(n log n) element-distinctness remark (App. D items 1–2);
journal choice. The sweep contributes only the empirical growth fits.

## 7. Phase 5 — Release and cleanup

- [ ] `tools/package_release.sh` → v0.3.0 assets + SHA-256.
- [ ] Clean-clone checklist passes end-to-end.
- [ ] Tag + publish release v0.3.0; update commit/version cited in report
      and manuscript.
- [ ] Delete `_OLD_RUNS_ARCHIVE_20260831/` (after confirming nothing in
      the paper cites a pre-freeze number).

---

## 8. Open-item → plan mapping

| Open item in manuscript v3 | Closed by |
|---|---|
| §4.2 note: per-density RaC/HPaC, ρ=1.0 crossover | Campaign C per-density (T4) + Phase 4 sentence |
| §4.2.1 note: Eager/Bounded lack the star matrix; ">8 GB" rows vs O(n)-space theorem | T3 diagnostic + campaign D star passes + rebuilt table + explanation paragraph |
| §4.4 + Conclusion notes: BPPF comparison not meaningful | Campaign G (v1-style autonomous sweep) replacing §4.4; per-breakpoint test demoted to validation |
| Report note: campaign E from reduced matrix | Campaign E full 4×10 matrix |
| App. D: Θ/Ω claims, journal | Not computational — needs Marco |

## Deviations

*(none yet — record any deviation here, dated, before rerunning the
affected campaign)*
