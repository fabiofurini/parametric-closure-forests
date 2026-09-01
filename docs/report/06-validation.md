# Validation

- **Exhaustive enumeration oracle** (CTest): every directed forest with $\le4$ vertices over a finite coefficient grid; 10 000 random forests up to 11 vertices; mixed-orientation path, binary and star trees up to 257 vertices; 6 000 in-forest and 6 000 out-forest instances plus 2 000 larger ones per orientation; plus the structural invariants (layers partition $V$, each is a closure increment, thresholds strictly decreasing).
- **Cross-algorithm differential agreement**: every campaign runs several algorithms on the same instance and compares partition, thresholds and canonical order through a 64-bit fingerprint. Over the sweep: *zero* disagreements ([Table 2](06-validation.md#table-2)).
- **Sanitizers and CI**: GCC Release, GCC Debug with the address and undefined-behaviour sanitizers, and Clang Debug; all three pass at the frozen commit (`results/TEST_REPORT_2026-08-31.md`).
- **Overflow**: `validate_instance` refuses any instance whose total absolute profit or weight would leave the exact-arithmetic margin ($`INT64\_MAX`/4$), before any algorithm runs.

<a id="table-2"></a>

**Table 2.** Number of instances benchmarked, of timed runs, and of cross-algorithm disagreements, per instance class. Every group aggregates all sizes, densities, coefficient families and seeds of that class. The `BPPF` comparison is listed apart, `BPPF` being an external baseline rather than one of our algorithms. Zero disagreements everywhere: on each instance the algorithms returned the same partition, the same thresholds and the same canonical order.

| instance class | $n$ | #inst | timed runs | disagreements |
|---|---|---|---|---|
| `mixed-forest` | $100$–$1\,000$ | 2 400 | 132 000 | 0 |
| `mixed-forest` | $10^4$–$10^5$ | 2 400 | 24 000 | 0 |
| `path-mixed` | $100$–$10^5$ | 600 | 7 200 | 0 |
| `binary-mixed` | $100$–$10^5$ | 600 | 7 200 | 0 |
| `star-mixed` | $100$–$10^5$ | 600 | 6 480 | 0 |
| `in-forest` | $100$–$10^5$ | 4 800 | 57 600 | 0 |
| `out-forest` | $100$–$10^5$ | 4 800 | 57 600 | 0 |
| total |  | 16 200 | 292 080 | 0 |


---

← [Instances](05-instances.md) · [Contents](README.md) · [The campaigns](07-the-campaigns.md) →
