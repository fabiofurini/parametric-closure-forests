# The algorithms, in one page

All of them solve the same problem and return the same object: given a directed forest with integer profits $p_i$ and strictly positive integer weights $w_i$, the ordered sequence of closure layers of $u(\lambda)=\max\{P(S)-\lambda W(S): S \text{ closed}\}$, with the exact rational threshold of each layer. All of ours use exact integer arithmetic: 64-bit coefficients, 128-bit cross-multiplication for every ratio comparison, no floating point in any decision path.

<a id="table-1"></a>

**Table 1.** The algorithms compared in this report: the class of forests each one applies to, its worst-case time and space bounds, and how it selects the next candidate. Bounds are those proved in the manuscript, except `BPPF`'s, which is the published bound of the parametric pseudoflow method on a graph with $n$ vertices and $m$ arcs. A forest has $m\le n-1$, i.e. $m=\mathcal O(n)$, so on *our* inputs `BPPF`'s bounds specialize to $\mathcal O(n^2\log n)$ time and $\mathcal O(n)$ space: its time bound is worse than that of every algorithm above it, which is the theoretical reason a forest-specific method is worth having.

|  | Applies to | Time | Space | Selection of the best candidate |
|---|---|---|---|---|
| `PaC` | any forest | $\mathcal O(n^2)$ | $\mathcal O(n)$ | linear scan |
| `DPaC` | any forest | $\mathcal O(n^2)$ | $\mathcal O(n)$ | linear scan, dual order |
| `HPaC` | any forest | $\mathcal O(n^2\log n)$ | $\mathcal O(n)$ | two candidate heaps |
| `DHPaC` | any forest | $\mathcal O(n^2\log n)$ | $\mathcal O(n)$ | two heaps, dual order |
| `HIPaC` | in-forests | $\mathcal O(n\log n)$ | $\mathcal O(n)$ | one heap over the vertices |
| `HOPaC` | out-forests | $\mathcal O(n\log n)$ | $\mathcal O(n)$ | one heap, dual order |
| `RaC` | any tree | $\mathcal O(n\log n)$ | $\mathcal O(n\log n)$ | none: top-tree contraction |
| `BPPF` | general graphs | $\mathcal O(mn\log n)$ | $\mathcal O(m)$ | external, parametric pseudoflow |
|  | *on a forest* | $\mathcal O(n^2\log n)$ | $\mathcal O(n)$ | *since $m\le n-1$* |


What each one does, and what the experiments below add:

- **`PaC`** peels the current best final vertices or contracts the best arc, finding the best candidate by a linear scan at every iteration. Slowest on random forests beyond $n\approx400$, but the most robust of the three on stars, precisely because it maintains nothing.
- **`DPaC`** is its dual: it builds the sequence from the lowest ratio upwards. It tracks `PaC` everywhere we measured.
- **`HPaC`** performs the same two moves, but keeps the candidates in two heaps, so only those touched by the last move are refreshed. Fastest of ours on random forests, paths and binary trees; penalized on a high-degree hub, where a single move invalidates a constant fraction of the candidates.
- **`DHPaC`** is its dual, within $25\%$ of it everywhere.
- **`HIPaC`** exploits out-degree $\le1$: the minimal preceding set of an arc is then a singleton, so one heap value per vertex suffices and no closure sums are propagated. Takes $0.52$–$0.75$ of `HPaC`'s time. **`HOPaC`** is the symmetric case (in-degree $\le1$): $0.57$–$0.78$.
- **`RaC`** contracts the tree in $\mathcal O(\log n)$ rake-and-compress rounds, computing cluster functions, then recovers the thresholds top-down. It is the only algorithm whose cost does not depend on how often a single vertex is touched – hence the winner on stars, by up to $250\times$.
- **`BPPF`** is the external baseline: it solves a strictly more general problem, evaluates minimum cuts at parameter values supplied by the caller, and uses fixed-point arithmetic – hence the precision caveat of [Comparison with parametric pseudoflow](12-comparison-with-parametric-pseudoflow.md). Its $\mathcal O(mn\log n)$ bound is stated for a general precedence graph; a forest has $m\le n-1$, so on the instances of this report it reads $\mathcal O(n^2\log n)$: a factor $n$ above the $\mathcal O(n\log n)$ of `RaC` and of the single-orientation variants, and a factor $\log n$ above the $\mathcal O(n^2)$ of `PaC`. The measured gap of [Comparison with parametric pseudoflow](12-comparison-with-parametric-pseudoflow.md) should be read against that: it is a factor of a few, far smaller than the gap between the bounds.

Two remarks that matter for reading the results. First, `PaC` and `HPaC` are the *same algorithm* under two schedules – the difference measured in [Medium sizes: direct scan versus heap](08-random-forests.md#medium-sizes-direct-scan-versus-heap) is entirely the cost of finding the maximum-ratio candidate. Second, `RaC` pays a structural overhead per component (cluster bookkeeping) that the others do not, which is why density matters so much in [Large sizes, and the effect of density](08-random-forests.md#large-sizes-and-the-effect-of-density): a sparse forest is many small components.

---

← [Summary](01-summary.md) · [Contents](README.md) · [Definitions and conventions](03-definitions-and-conventions.md) →
