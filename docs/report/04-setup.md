# Setup

### Machine and build

Intel Core i7-12700, 32 GB RAM, Ubuntu 22.04.5 (kernel 6.8), GCC 11.4.0 at `-O3`, single-threaded. Each benchmark process pinned to one physical core (`taskset`); the six campaign lanes ran on distinct cores, never two on the same core. CPU governor `powersave` (no passwordless root on this machine), so absolute times carry ordinary frequency-scaling noise – which is one reason every comparison is a paired same-instance ratio.

### What is timed

Only the algorithm call (`std::chrono::steady_clock`); parsing, result hashing and correctness comparison sit outside the timed region. Repetitions: 11 for random forests with $n\le1\,000$, 3 elsewhere. Algorithm order shuffled per repetition, so no algorithm is systematically favoured by the CPU frequency state.

### Memory, and what “peak RSS” means

RSS is the *resident set size*: the amount of physical RAM the process has mapped at a given instant. Peak RSS is its maximum over the run, read from `getrusage(RUSAGE_SELF).ru_maxrss`. Two properties matter when reading memory figures. It is a *process-lifetime* peak and never decreases, so in an invocation that benchmarks several algorithms the value recorded for the second includes the peak of the first – memory is therefore quoted only from single-algorithm invocations ([Implementation note: heap policy](11-implementation-note-heap-policy.md)). And it counts pages actually resident, so it includes allocator overhead and is precisely the quantity that decides whether a run survives a memory ceiling.

### Statistics

Absolute times: median over repetitions, then median over instances. Comparisons: *paired* per instance, reported as the median of the per-instance ratios together with their IQR ([Definitions and conventions](03-definitions-and-conventions.md)), never a ratio of aggregate means. The median is chosen because it is invariant under inversion of the comparison (the arithmetic mean of ratios is not: it depends on which algorithm sits in the denominator), because the timing noise has an asymmetric right tail by construction (interference can only slow a run down, never speed it up), and because it is the conservative choice on every comparison where we claim an advantage – on the `BPPF` comparison at $n=1\,000$ the three aggregates are $4.5$ (median), $5.8$ (geometric mean) and $8.7$ (arithmetic mean).

---

← [Definitions and conventions](03-definitions-and-conventions.md) · [Contents](README.md) · [Instances](05-instances.md) →
