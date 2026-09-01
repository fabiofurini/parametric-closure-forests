# The campaigns

A *campaign* is one block of the sweep: a set of instances, the algorithms run on them, and the number of repetitions. The split is not cosmetic – each campaign answers one question, and keeping them separate is what allows a result to be attributed to a cause:

- **A** is correctness only, on instances small enough to be solved by brute force, so that every algorithm can be checked against an independent oracle rather than against another algorithm.
- **B** and **C** are the same random topology at two scales. B is where all five algorithms still fit, so it is the one place where every pairwise comparison is available; C drops the two quadratic ones and asks how the rest scale.
- **D** fixes the shape (path, balanced binary tree, star) and varies nothing but orientations and coefficients, which isolates the effect of topology – and produces the one case where the theoretical separation between our algorithms becomes visible.
- **E** restricts the orientation (in-forest, out-forest) to measure what a specialized algorithm gains from knowing it in advance.
- **G** is the external comparison against parametric pseudoflow. It sits on the same instances as B, so its numbers can be read against the rest of the study.

All campaigns were frozen in `docs/EXPERIMENTAL_PLAN_V3.md` before any run, together with the two size cutoffs, so that no scoping decision was taken after seeing results. [Table 3](07-the-campaigns.md#table-3) gives the definitions, [Table 4](07-the-campaigns.md#table-4) how much work each algorithm actually did, and [Table 2](06-validation.md#table-2) the correctness outcome per campaign.

<a id="table-3"></a>

**Table 3.** Campaign definitions. Every campaign uses all six coefficient families and ten seeds; the random topologies use all four densities. Two preregistered size cutoffs apply, in both cases because the asymptotic trend is already established below them and running further would consume hours without adding information: `PaC`/`DPaC` stop at $n=20\,000$ on random forests, and `HPaC`/`DHPaC` stop at $n=20\,000$ on stars (where `PaC` is cheap and runs the full range instead).

|  | Topology | Sizes $n$ | Inst./size | Reps | Algorithms |
|---|---|---|---|---|---|
| A | all six | $\le11$ (exhaustive at 4) | – | – | all, against the enumeration oracle |
| B | `mixed-forest` | $100,200,\dots,1\,000$ | 240 | 11 | `PaC`, `DPaC`, `HPaC`, `DHPaC`, `RaC` |
| C | `mixed-forest` | $10\,000,\dots,100\,000$ | 240 | 3 | `HPaC`, `DHPaC`, `RaC`; `PaC`, `DPaC` at $10^4$, $2\cdot10^4$ |
| D | `path-`, `binary-`, `star-mixed` | 10 sizes, $100\dots100\,000$ | 60 | 3 | `HPaC`, `RaC`, `DHPaC`, `PaC`, `DPaC` |
| E | `in-`, `out-forest` | 20 sizes, $100\dots100\,000$ | 240 | 3 | `HPaC`, `DHPaC`, `HIPaC`/`HOPaC`, `RaC` |
| G | `mixed-forest` | $100,200,\dots,1\,000$ | 240 | 3 | `HPaC` against `BPPF` |


<a id="table-4"></a>

**Table 4.** Work actually done per algorithm over the sweep. The runs-per-instance column reflects the mix of repetition counts and cutoffs: `PaC` and `DPaC` appear on fewer instances (size cutoffs) but with more repetitions each, since they were mostly exercised on the medium campaign where 11 repetitions were used. `RaC` appears on the most instances, being the only algorithm run on every class at every size.

| algorithm | instances | timed runs | runs/instance |
|---|---|---|---|
| `PaC` | 4 080 | 31 200 | 7.6 |
| `DPaC` | 3 480 | 29 400 | 8.4 |
| `HPaC` | 16 080 | 67 440 | 4.2 |
| `DHPaC` | 16 080 | 67 440 | 4.2 |
| `HIPaC` | 4 800 | 14 400 | 3.0 |
| `HOPaC` | 4 800 | 14 400 | 3.0 |
| `RaC` | 16 200 | 67 800 | 4.2 |
| total | 16 200 | 292 080 |  |


---

← [Validation](06-validation.md) · [Contents](README.md) · [Random forests](08-random-forests.md) →
