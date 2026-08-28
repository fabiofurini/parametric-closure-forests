#!/usr/bin/env python3
"""Convert a .pcf instance plus one fixed rational lambda into the DIMACS-style
input consumed by third_party/bppf/pseudopar.c (BPPF).

This intentionally does NOT drive BPPF's own multi-breakpoint parametric
sweep. Encoding our affine node weights p_i - lambda*w_i as a single
genuinely parametric BPPF network requires arc capacities that are
non-decreasing towards the source and non-increasing towards the sink over
the whole sweep range, which does not hold uniformly here whenever an
item's coefficient changes sign inside the range. Baking one exact lambda
into fixed integer capacities and calling BPPF once per lambda avoids that
pitfall entirely: each call is the textbook Picard maximum-weight-closure
reduction at a single point, independently correct, and BPPF is used purely
as a fast, independent maximum-flow/minimum-cut engine (docs/PIANO_PARTE_COMPUTAZIONALE.md
section 7.2, "Oracle 2"). Running it at a sequence of lambdas (typically our
own algorithms' reported breakpoints) is how campaign F and the max-flow
oracle in tools/verify_with_bppf.py both use it.

Node numbering in the emitted file: 1 = source, 2..n+1 = pcf items 0..n-1
(so item i is file node i+2), n+2 = sink.

Coefficients are scaled to stay exact: for lambda = a/b in lowest terms with
b > 0, closures are ranked identically by c_i(lambda) = p_i - lambda*w_i and
by b*p_i - a*w_i (a positive rescaling), so every arc capacity below is the
exact integer b*p_i - a*w_i, with no floating point involved before it
reaches BPPF's own atof/llround parsing (prec 0, so every capacity token is
parsed back as the exact integer we wrote).
"""
from __future__ import annotations

import argparse
from fractions import Fraction
from pathlib import Path


def read_pcf(path: Path) -> tuple[int, list[int], list[int], list[tuple[int, int]]]:
    tokens = path.read_text(encoding="utf-8").split()
    cursor = 0

    def take(expected: str) -> None:
        nonlocal cursor
        assert tokens[cursor] == expected, f"expected {expected!r}, got {tokens[cursor]!r}"
        cursor += 1

    take("pcf"); take("1")
    take("n"); n = int(tokens[cursor]); cursor += 1
    take("profits"); profit = [int(v) for v in tokens[cursor:cursor + n]]; cursor += n
    take("weights"); weight = [int(v) for v in tokens[cursor:cursor + n]]; cursor += n
    take("arcs"); m = int(tokens[cursor]); cursor += 1
    arcs = []
    for _ in range(m):
        tail, head = int(tokens[cursor]) - 1, int(tokens[cursor + 1]) - 1
        cursor += 2
        arcs.append((tail, head))
    return n, profit, weight, arcs


def convert(instance_path: Path, lam: Fraction, output_path: Path) -> None:
    n, profit, weight, arcs = read_pcf(instance_path)
    a, b = lam.numerator, lam.denominator  # lam == a/b, b > 0
    scaled = [b * profit[i] - a * weight[i] for i in range(n)]
    big = sum(abs(value) for value in scaled) + 1
    if big >= 2 ** 53:
        raise ValueError(
            f"{instance_path}: scaled coefficients too large for BPPF's double-precision "
            f"capacity parsing (need |value| < 2**53, got big={big}); this instance/lambda "
            "pair is out of scope for the BPPF baseline (see docs/EXPERIMENTAL_PROTOCOL.md)."
        )

    source, sink = 1, n + 2
    lines: list[str] = []
    arc_lines: list[str] = []
    for i, value in enumerate(scaled):
        node = i + 2
        if value >= 0:
            arc_lines.append(f"a {source} {node} 0 {value}")
        else:
            arc_lines.append(f"a {node} {sink} 0 {-value}")
    for tail, head in arcs:
        arc_lines.append(f"a {tail + 2} {head + 2} {big}")

    lines.append(f"p sequence {n + 2} {len(arc_lines)} 0 1 0")
    lines.append(f"n {source} s")
    lines.append(f"n {sink} t")
    lines.extend(arc_lines)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--instance", type=Path, required=True)
    parser.add_argument("--lambda-num", type=int, required=True)
    parser.add_argument("--lambda-den", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    convert(arguments.instance, Fraction(arguments.lambda_num, arguments.lambda_den), arguments.output)


if __name__ == "__main__":
    main()
