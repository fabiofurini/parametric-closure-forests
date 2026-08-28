"""Closure-specific affine-coefficient families shared by every instance generator.

These six families are the ones frozen in docs/PIANO_PARTE_COMPUTAZIONALE.md
section 8.3. Names and generation rules are motivated purely by the shape of
the resulting profit-to-weight ratios p_i/w_i, never by a knapsack class:

- independent-positive: p, w independent and positive -> dispersed ratios.
- independent-signed: w > 0, p signed -> locally unfavourable nodes.
- correlated: p close to w -> concentrated ratios.
- anti-correlated: p close to (range - w) -> more heterogeneous ratios.
- near-ties: many nodes share a common target ratio up to a small integer
  jitter -> stresses exact rational comparisons near-equal but distinct.
- exact-ties: many nodes share one exact rational ratio -> stresses the
  canonicalization rule that merges consecutive macroitems at equal ratio.

Every function returns (profits, weights) with weights strictly positive, as
required by section 1 of the plan.
"""
from __future__ import annotations

import random

FAMILIES = (
    "independent-positive",
    "independent-signed",
    "correlated",
    "anti-correlated",
    "near-ties",
    "exact-ties",
)


def make_coefficients(n: int, family: str, rng: random.Random) -> tuple[list[int], list[int]]:
    if family == "independent-positive":
        weights = [rng.randint(1, 1000) for _ in range(n)]
        profits = [rng.randint(1, 1000) for _ in range(n)]
        return profits, weights

    if family == "independent-signed":
        weights = [rng.randint(1, 1000) for _ in range(n)]
        profits = [rng.randint(-1000, 1000) for _ in range(n)]
        return profits, weights

    if family == "correlated":
        weights = [rng.randint(1, 1000) for _ in range(n)]
        profits = [w + rng.randint(-50, 50) for w in weights]
        return profits, weights

    if family == "anti-correlated":
        weights = [rng.randint(1, 1000) for _ in range(n)]
        profits = [(1001 - w) + rng.randint(-50, 50) for w in weights]
        return profits, weights

    if family == "near-ties":
        num, den = rng.randint(1, 20), rng.randint(1, 20)
        weights, profits = [], []
        for _ in range(n):
            t = rng.randint(1, 50)
            w = den * t
            jitter = rng.choice([-2, -1, 1, 2])
            weights.append(w)
            profits.append(num * t + jitter)
        return profits, weights

    if family == "exact-ties":
        num, den = rng.randint(1, 20), rng.randint(1, 20)
        weights, profits = [], []
        num_groups = max(1, n // 20)
        group_ratio = [(rng.randint(1, 20), rng.randint(1, 20)) for _ in range(num_groups)]
        for i in range(n):
            gn, gd = group_ratio[i % num_groups]
            t = rng.randint(1, 50)
            weights.append(gd * t)
            profits.append(gn * t)
        return profits, weights

    raise ValueError(f"unknown coefficient family: {family}")
