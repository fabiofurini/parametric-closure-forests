# Definitions and conventions

Terms used throughout, fixed here once.

- **Closure layer.** One block $\mathcal I_r$ of the canonical partition of the vertex set induced by the parametric solution: the vertices that enter the optimal closed set exactly when $\lambda$ crosses the breakpoint $\lambda_r$. “Number of layers” equals the number of breakpoints of $u(\lambda)$, so it measures how much parametric structure an instance has, and it bounds the number of iterations of every algorithm here.
- **Threshold** of a vertex: the breakpoint at which that vertex enters the optimal closed set; vertices with equal threshold form one layer.
- **Density $\varrho$.** The probability with which the generator adds each candidate arc. A forest with density $\varrho$ has $\varrho(n-1)$ arcs and $n-\varrho(n-1)$ connected components in expectation, so $\varrho=1.0$ gives one spanning tree and $\varrho=0.3$ a forest of many small trees ([Figure 1](05-instances.md#figure-1)).
- **Coefficient family.** The rule used to draw the profits and weights of an instance; six are used ([Instances](05-instances.md)). It controls the *shape* of the ratios $p_i/w_i$ and hence how many layers appear.
- **Paired ratio.** The ratio of two algorithms' times *on the same instance*. Reported as the median over instances, never as a ratio of two aggregates: pairing removes the instance-to-instance variation that would otherwise swamp the comparison.
- **IQR (interquartile range).** $Q_3-Q_1$: the width of the band containing the central half of the observations. It is to the median what the standard deviation is to the mean, but insensitive to the tails. Beside a median ratio, a large IQR signals that the population mixes regimes instead of scattering around one value – exactly what happens across densities in [Large sizes, and the effect of density](08-random-forests.md#large-sizes-and-the-effect-of-density).
- **Relative IQR** ([Dispersion of the measurements](13-dispersion-of-the-measurements.md)): the IQR of the repetitions of one instance divided by that instance's median time, in percent. It quantifies measurement noise, not algorithmic variability.
- **Peak RSS** (resident set size): the maximum amount of physical RAM the process had mapped during the run, from `getrusage(RUSAGE_SELF).ru_maxrss`. See [Setup](04-setup.md) for the two caveats that make it usable only for single-algorithm runs.
- **Censored run.** A run killed by the time limit (300 s) or the memory ceiling (8 GiB), hence without a measured time. There are none in this study; the term appears only to state that.
- **Campaign.** One preregistered block of the sweep – a set of instances plus the algorithms run on them (B, C, D, E, G).
- **Tree of a forest, and its size.** A connected component of the *underlying undirected* graph, and its number of vertices. Orientations are irrelevant to this notion: a forest of in-trees and a forest of mixed orientations built with the same seed have the same trees. A vertex with no incident arc is a tree of size 1, called *isolated* ([How many trees, and how big?](05-instances.md#how-many-trees-and-how-big)).
- **SHA-256 checksum.** A 256-bit fingerprint of a file, computed with the standard SHA-2 hash function: any change to the file's bytes, even a single one, changes the fingerprint, and no one can construct a different file with the same fingerprint. We record it for every instance file (`instances/manifests/*.json`) and for every archive in the data release, so that a regenerated or downloaded instance can be proved byte-for-byte identical to the one measured here – a reproducibility device, not a security one. It is unrelated to the 64-bit `sequence_hash` used to compare algorithm *outputs* ([Validation](06-validation.md)), which is a cheap non-cryptographic hash.

---

← [The algorithms, in one page](02-the-algorithms-in-one-page.md) · [Contents](README.md) · [Setup](04-setup.md) →
