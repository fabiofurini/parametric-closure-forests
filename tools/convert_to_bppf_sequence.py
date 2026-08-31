#!/usr/bin/env python3
"""Convert a .pcf instance plus a LIST of rational lambdas into a single
DIMACS-style "sequence" input for third_party/bppf/pseudopar.c (BPPF),
using BPPF's native two-number-per-arc affine capacity encoding instead of
tools/convert_to_bppf.py's one-lambda-baked-into-fixed-integers encoding.

Why this exists: tools/convert_to_bppf.py deliberately bakes one exact
lambda into fixed integer arc capacities and calls BPPF once per lambda
(see its docstring) -- correct and exact, but means a k-breakpoint sweep
costs k process spawns. BPPF's own "sequence" input format supports a list
of k probe values in one file/process; each arc line for a source- or
sink-adjacent arc then carries TWO numbers (cst, wt) instead of one fixed
capacity, and BPPF evaluates, per pseudopar.c's ACTIVE computeArcCapacity
(the USE_ARC_MACRO branch is left undefined, so the plain-function
definition applies uniformly to every arc, source/sink/internal alike):

    capacity(param) = max(0, wt + param*cst)

with cst=0 (a constant) for internal precedence arcs. Choosing cst=-w_i on
item i's source-adjacent arc and cst=+w_i on its sink-adjacent arc (both
with wt=p_i) makes capacity(lambda) equal max(0, p_i - lambda*w_i) and
max(0, lambda*w_i - p_i) respectively -- the same maximum-weight-closure
reduction tools/convert_to_bppf.py already uses at a single lambda, just
left affine in lambda instead of pre-baked into one number. See the sign
comment inside convert_sequence() for why the source arc needs the MINUS
sign specifically (BPPF's own monotonicity check rejects the naive +w_i
choice). Internal (precedence) arcs stay a single fixed large capacity,
same as tools/convert_to_bppf.py.

This is NOT the "complement" network some published BPPF usage notes for
this problem describe (i.e. do not copy signs from other write-ups without
re-deriving them against this module's own convention) -- it is derived
directly from, and should always be validated against,
tools/convert_to_bppf.py's already-trusted single-lambda reduction: see
tools/validate_bppf_sequence.py.

Precision: unlike the single-lambda converter (exact integers, no
rounding), BPPF's own arithmetic on a multi-value sequence is fixed-point
with `prec` decimal digits (APP_VAL = 10**prec in pseudopar.c). Two
breakpoints closer together than 10**-prec can therefore be merged by BPPF
itself -- this is an expected, reportable precision artifact (see
docs/EXPERIMENTAL_PROTOCOL.md once the native-speed campaign is written up),
not a bug to hide.
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


def convert_sequence(instance_path: Path, lambdas: list[Fraction], prec: int, output_path: Path) -> None:
    if not lambdas:
        raise ValueError("convert_sequence requires at least one lambda")
    n, profit, weight, arcs = read_pcf(instance_path)

    source, sink = 1, n + 2
    arc_lines: list[str] = []
    for i in range(n):
        node = i + 2
        # pseudopar.c's ACTIVE computeArcCapacity (USE_ARC_MACRO is left
        # undefined, so the plain-function branch applies to every arc) is
        # capacity(param) = max(0, wt + param*cst) -- there is no separate
        # source/sink case in the formula itself, the distinction is purely
        # which sign of cst you supply. Probe lambdas are fed in DEcreasing
        # order (same order run_bppf_campaign.py's midpoints() already
        # produces, matching this codebase's own breakpoint convention:
        # M_1 subset M_2 subset ... as lambda decreases), so as the
        # parameter *index* advances, the raw lambda value decreases:
        #   source arc: cst = -w_i -> wt + param*cst = p_i - lambda*w_i,
        #     which INCREASES as the index advances (lambda falling) --
        #     satisfies BPPF's "source-adjacent capacity must not decrease
        #     with the parameter index" requirement.
        #   sink arc:   wt = -p_i, cst = +w_i -> wt + param*cst
        #     = lambda*w_i - p_i, which DEcreases as the index advances
        #     (lambda falling) -- satisfies the opposite (non-increasing)
        #     requirement for sink-adjacent arcs.
        # (Earlier, wrong attempts caught by tools/validate_bppf_sequence.py:
        # cst=+w_i on both arcs made pseudopar.c abort with an explicit
        # "capacity decreases" fatal check on the source arc; wt=+p_i on the
        # sink arc, instead of -p_i, silently made every item look
        # permanently excluded at every probe -- both wrong in ways that
        # would not have been caught without validating against HPaC.)
        arc_lines.append(f"a {source} {node} {-weight[i]} {profit[i]}")
        arc_lines.append(f"a {node} {sink} {weight[i]} {-profit[i]}")
    big = sum(abs(p) for p in profit) + sum(abs(w) for w in weight) + 1
    for tail, head in arcs:
        arc_lines.append(f"a {tail + 2} {head + 2} {big}")

    # Every number in this file, including `big`, gets multiplied by
    # APP_VAL=10**prec inside pseudopar.c before it is stored as a 64-bit
    # integer (ac->wt/ac->cst = llround(value * APP_VAL)); tools/convert_to_bppf.py's
    # single-lambda encoding never pays this because it always uses prec=0
    # (one exact point, capacities baked in directly). This is therefore a
    # genuine SIZE limit of the native multi-lambda encoding that grows both
    # with the instance (via `big`) and with how much precision the probe
    # sequence needs (via `prec`, raised to resolve closely-spaced
    # breakpoints) -- not a matter of the encoding being "wrong" for large
    # instances, but of it running out of exactly-representable integer
    # range (double-precision: 2**53) for them. Instances/precisions past
    # this bound are out of scope for the native-speed comparison and must
    # be reported as skipped, the same way tools/convert_to_bppf.py already
    # does for its own (different, prec-independent) overflow condition --
    # never silently truncated.
    if big * (10 ** prec) >= 2 ** 53:
        raise ValueError(
            f"{instance_path}: scaled coefficients too large for BPPF's double-precision "
            f"capacity parsing at prec={prec} (need big*10**prec < 2**53, got "
            f"big={big}, big*10**prec={big * (10 ** prec)}); this instance/precision pair is "
            "out of scope for the native-speed comparison (see docs/EXPERIMENTAL_PROTOCOL.md "
            "once written up, and tools/convert_to_bppf.py's own analogous guard)."
        )

    lambda_tokens = " ".join(f"{float(lam):.{prec}f}" for lam in lambdas)
    lines = [
        f"p sequence {n + 2} {len(arc_lines)} {prec} {len(lambdas)} {lambda_tokens}",
        f"n {source} s",
        f"n {sink} t",
        *arc_lines,
    ]
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def closures_from_sequence_output(stdout: str, n: int, k: int) -> list[set[int]]:
    """One closure per probe index (1-based), reconstructed from BPPF's
    displayBreakpoints output (`n <node_id> <breakpoint_index>` lines,
    pseudopar.c:1452-1453): node is in the closure at probe j iff its
    recorded breakpoint index is <= j (see convert_to_bppf_sequence.py
    module docstring / tools/validate_bppf_sequence.py for how this was
    checked empirically -- do not trust this without that validation)."""
    breakpoint_of: dict[int, int] = {}
    for line in stdout.splitlines():
        if not line.startswith("n "):
            continue
        _, node_id, breakpoint = line.split()
        node_id, breakpoint = int(node_id), int(breakpoint)
        if 2 <= node_id <= n + 1:
            breakpoint_of[node_id - 2] = breakpoint
    return [
        {item for item, bp in breakpoint_of.items() if bp <= probe_index}
        for probe_index in range(1, k + 1)
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--instance", type=Path, required=True)
    parser.add_argument("--lambdas", type=str, required=True,
                         help="comma-separated list of num/den fractions, e.g. 1/2,3/2,7/3")
    parser.add_argument("--prec", type=int, default=6)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    lambdas = [Fraction(token) for token in arguments.lambdas.split(",")]
    convert_sequence(arguments.instance, lambdas, arguments.prec, arguments.output)


if __name__ == "__main__":
    main()
