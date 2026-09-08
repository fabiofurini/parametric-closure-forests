#!/usr/bin/env python3
"""Convert a .pcf instance into the input format of Hochbaum's FULLY
parametric HPF solver (hochbaumGroup/pseudoflow-parametric-cut-v2).

Unlike the bounded-precision "simple parametric" solver used by earlier versions of this study (removed 2026-09-08), which only
evaluates minimum cuts at parameter values somebody else supplies, this one
is given nothing but a parameter RANGE and computes every breakpoint by
itself. It is therefore the implementation the manuscript should race
against: both sides solve the same problem from scratch.

Encoding. The solver requires source-adjacent arc capacities to be monotone
NON-DECREASING in its parameter and sink-adjacent ones non-increasing, with
both of the 2-piecewise-linear form max(0, const + mult*param). The
manuscript's vertex contribution is p_i - lambda*w_i, which decreases in
lambda, so we run the solver on the REVERSED parameter

    mu = -lambda,

giving vertex value p_i + mu*w_i. The standard maximum-closure/minimum-cut
reduction then becomes

    source -> i : const = +p_i, mult = +w_i   (non-negative, as required)
    i -> sink   : const = -p_i, mult = -w_i   (non-positive, as required)
    u -> v      : const = big,  mult = 0      for each precedence arc (u,v)

so that at parameter mu the source set is exactly the maximum closure at
lambda = -mu. A vertex's reported "lambda sourceset breakpoint" mu_v is
therefore its threshold in the manuscript's sense, negated: lambda_v = -mu_v
(Definition 3). Vertices sharing a threshold form one closure layer.

The range is derived from the instance alone -- every ratio p_i/w_i lies in
[-max|p_i|, max|p_i|] because w_i >= 1 -- so nothing about the solution is
smuggled in.
"""
from __future__ import annotations

from pathlib import Path


def read_pcf(path: Path) -> tuple[int, list[int], list[int], list[tuple[int, int]]]:
    """Parse a .pcf instance (docs/INSTANCE_FORMAT.md): returns
    (n, profits, weights, arcs) with vertices re-indexed from 0. An arc
    (tail, head) means x_tail <= x_head, i.e. tail precedes head."""
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


def convert(instance_path: Path, output_path: Path) -> tuple[int, int]:
    """Write the fully-parametric-HPF input file. Returns (n, mu_bound)."""
    n, profit, weight, arcs = read_pcf(instance_path)

    # Nodes are labeled 0 .. #nodes-1; vertex i of the instance becomes i+1.
    source, sink = 0, n + 1
    big = sum(abs(p) for p in profit) + sum(abs(w) for w in weight) + 1
    bound = max((abs(p) for p in profit), default=1) + 1

    arc_lines = []
    for i in range(n):
        arc_lines.append(f"a {source} {i + 1} {profit[i]} {weight[i]}")
        arc_lines.append(f"a {i + 1} {sink} {-profit[i]} {-weight[i]}")
    for tail, head in arcs:
        arc_lines.append(f"a {tail + 1} {head + 1} {big} 0")

    lines = [
        f"c fully parametric HPF input generated from {instance_path.name}",
        "c parameter is mu = -lambda; vertex threshold lambda_v = -mu_v",
        f"p {n + 2} {len(arc_lines)} {-bound} {bound}",
        f"n {source} s",
        f"n {sink} t",
        *arc_lines,
    ]
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return n, bound


def parse_output(output_path: Path, n: int) -> tuple[int, dict, float]:
    """Read the solver's output file.

    Returns (num_intervals, {vertex: reported mu}, solve_seconds).

    NOTE the v2 C output does not follow its own README. The README documents
    one `n <node-id> <breakpoint>` line per node, but hpf.c's writeOutput
    instead sorts the nodes by their `cuts` value and emits one line per
    distinct value,

        l <mu value> <node-id> <node-id> ...

    grouping together every node with that value (the README's `l` line of
    interval bounds is commented out in the source). Node 0 is the source and
    node n+1 the sink; both carry sentinel values (LAMBDA_LOW / LAMBDA_HIGH)
    and are dropped here.

    The `t` line reports read/initialize/solve separately, so the third field
    is the pure solve time, excluding input parsing -- the same convention the
    simple-parametric comparison already uses.
    """
    threshold_mu: dict[int, float] = {}
    solve_seconds = float("nan")
    num_intervals = 0

    for line in output_path.read_text(encoding="utf-8").splitlines():
        fields = line.split()
        if not fields:
            continue
        if fields[0] == "t":
            solve_seconds = float(fields[3])
        elif fields[0] == "p":
            num_intervals = int(fields[1])
        elif fields[0] == "l":
            mu = float(fields[1])
            for token in fields[2:]:
                node = int(token)
                if 1 <= node <= n:
                    threshold_mu[node - 1] = mu
    return num_intervals, threshold_mu, solve_seconds


def layers_from_thresholds(threshold_mu: dict, n: int) -> list[tuple[float, set]]:
    """Group vertices by threshold and order them as the manuscript does:
    decreasing lambda = -mu, i.e. increasing mu. Returns [(lambda, layer)]."""
    grouped: dict[float, set] = {}
    for vertex, mu in threshold_mu.items():
        grouped.setdefault(mu, set()).add(vertex)
    return [(-mu, grouped[mu]) for mu in sorted(grouped)]


def _main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instance", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    n, bound = convert(args.instance, args.output)
    print(f"wrote {args.output} (n={n}, mu range [{-bound}, {bound}])")


if __name__ == "__main__":
    _main()
