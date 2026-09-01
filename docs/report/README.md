# Parametric Maximum Closure on Directed Forests
## Computational report — data release `v0.3.0`

Valerio Dose · Fabio Furini · Marco Locatelli

*Browsable edition of [`report/computational_report.pdf`](../../report/computational_report.pdf); generated from the same LaTeX source by `tools/emit_markdown_report.py`, so the numbers are the same.*

This report accompanies the manuscript *“On parametric Maximum Closure Problems over precedence forests”*. The manuscript states the algorithms, their analysis, and the few experiments needed to support the theory. This report is the complement: the full experimental record, and specifically the material the manuscript does not carry –

- absolute running times of *every* algorithm at *every* size of every campaign, not a selection;
- breakdowns by *arc density* and by *coefficient family*, which is where the interesting structure turns out to be ([Large sizes, and the effect of density](08-random-forests.md#large-sizes-and-the-effect-of-density));
- what the instance generators actually produced – arcs, components, number of closure layers – so that a reader can tell what each parameter buys ([Instances](05-instances.md));
- the dispersion of the raw measurements, so that any reported ratio can be compared against the noise it rests on ([Dispersion of the measurements](13-dispersion-of-the-measurements.md));
- the implementation analysis behind the $\mathcal O(n)$ space bound ([Implementation note: heap policy](11-implementation-note-heap-policy.md)), and the exact protocol, including what “peak RSS” means and why memory is only quoted from single-algorithm runs.

Every table and plot is generated from the raw benchmark data by `tools/build_report.sh`; no number is hand-typed.

### How to read the figures

Every result in this report is presented in the same shape: a table of numbers on the left, a plot of *the same numbers* on the right, and one caption below both. Every caption follows the same three-part order:

1. **what is reported** – the quantity and the statistic, spelled out (for instance “median CPU time in milliseconds, the median over instances of the per-instance median over repetitions”);
2. **on which instances** – the instance class, the sizes, and how many instances each reported value aggregates;
3. **what we observe** – the reading of the figure, and where possible the mechanism behind it.

Unless a caption says otherwise, every time is CPU time in milliseconds, every “median” is taken over instances of the per-instance median over repetitions, and every ratio is a *paired* per-instance ratio ([Definitions and conventions](03-definitions-and-conventions.md)).


## Contents

- [Summary](01-summary.md)
- [The algorithms, in one page](02-the-algorithms-in-one-page.md)
- [Definitions and conventions](03-definitions-and-conventions.md)
- [Setup](04-setup.md)
- [Instances](05-instances.md)
- [Validation](06-validation.md)
- [The campaigns](07-the-campaigns.md)
- [Random forests](08-random-forests.md)
- [Structured classes](09-structured-classes.md)
- [Single orientations](10-single-orientations.md)
- [Implementation note: heap policy](11-implementation-note-heap-policy.md)
- [Comparison with parametric pseudoflow](12-comparison-with-parametric-pseudoflow.md)
- [Dispersion of the measurements](13-dispersion-of-the-measurements.md)

### Appendix

- [Per-family detail at every size](14-per-family-detail-at-every-size.md)
- [Reproducing this report](15-reproducing-this-report.md)

---

Next: [Summary](01-summary.md) →
