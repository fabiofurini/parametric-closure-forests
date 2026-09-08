# Summary

- **Sweep.** One frozen commit, one machine, 2026-08-31/09-01: 16 200 instances, 292 080 timed runs, seven algorithms; plus, on 2026-09-08, the race against the external fully parametric pseudoflow solver `FPHPF` ([Comparison with the fully parametric pseudoflow solver](12-comparison-with-the-fully-parametric-pseudoflow-solver.md)). No run hit the 300 s timeout or the 8 GiB memory ceiling, so nothing is censored.
- **Correctness.** Zero cross-algorithm disagreements ([Validation](06-validation.md)), on top of an exhaustive enumeration oracle on small instances and sanitizer builds.
- **Random forests, paths, binary trees.** `HPaC` is the fastest of our algorithms: $2$–$13\times$ `RaC` depending on size and density, and faster than the direct scan `PaC` from $n\approx400$ on.
- **Stars.** The ordering inverts: `RaC` is $\approx250\times$ `HPaC` at $n=20\,000$. Any heap-based schedule pays $\Theta(n)$ maintenance per event on a hub; `PaC`, which maintains no candidate structure, resists an order of magnitude better than `HPaC`.
- **Single orientations.** `HIPaC`/`HOPaC` take $0.52$–$0.78$ of `HPaC`'s time, stable up to $n=10^5$.
- **Against pseudoflow.** Both solving each instance from scratch, `HPaC` returns the same closure layers as the fully parametric pseudoflow solver `FPHPF` on all 2 400 instances with $n\le1\,000$ and is faster on every one of them, by a median factor $9$ at $n=100$ rising to $28$ at $n=1\,000$ – and to about $250$, $550$, $1\,300$ and $4\,000$ at $n=10^4,2\cdot10^4,5\cdot10^4,10^5$. From $n=10^4$ on, `FPHPF`'s fixed tolerance $10^{-7}$ merges consecutive layers closer than $2\cdot10^{-7}$ ([Comparison with the fully parametric pseudoflow solver](12-comparison-with-the-fully-parametric-pseudoflow-solver.md)).
- **Two facts that organize everything else.** The *topology* decides which algorithm wins – density moves the margin by an order of magnitude and the star class inverts it outright – while the *coefficient family* decides only how much parametric structure exists, moving absolute times but never the ranking. And the data structure inside one algorithm can matter as much as the choice of algorithm: the two heap policies of [Implementation note: heap policy](11-implementation-note-heap-policy.md) differ by $4\times$ in time and two orders of magnitude in memory, at identical output and identical asymptotic bounds.

---

← [Overview](README.md) · [Contents](README.md) · [The algorithms, in one page](02-the-algorithms-in-one-page.md) →
