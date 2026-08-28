#!/usr/bin/env python3
"""Oracle 2 (docs/PIANO_PARTE_COMPUTAZIONALE.md section 7.2): verify that the
closure sequence returned by one of this repository's own algorithms is
optimal at a fixed lambda, using BPPF (third_party/bppf/pseudopar.c) as an
independent maximum-flow/minimum-cut engine.

For a chosen rational lambda, this script:

1. runs pcf_solve to get the full macroitem sequence for --algorithm;
2. derives that algorithm's closure at lambda (union of macroitems whose
   ratio is > lambda; lambda must not equal a returned breakpoint exactly,
   to keep the membership unambiguous -- use --lambda-num/--lambda-den
   strictly between two consecutive breakpoints, e.g. from --midpoint-index);
3. converts the instance and lambda to a BPPF DIMACS file
   (tools/convert_to_bppf.py) and runs the breakpoint-instrumented
   pcf_bppf_oracle binary on it;
4. reports whether the two closures are identical, and exits non-zero if not.

This never re-implements a closure algorithm: correctness is established by
agreement with BPPF's independent min-cut computation, not by comparing our
own algorithms against each other.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from fractions import Fraction
from pathlib import Path

from convert_to_bppf import convert, read_pcf


def own_closure_at_lambda(pcf_solve: Path, instance: Path, algorithm: str, lam: Fraction) -> set[int]:
    completed = subprocess.run(
        [str(pcf_solve), "--instance", str(instance), "--algorithm", algorithm],
        check=True, text=True, capture_output=True,
    )
    closure: set[int] = set()
    for line in completed.stdout.splitlines():
        if not line.startswith("macroitem "):
            continue
        parts = line.split()
        ratio_token = parts[3]  # "P/W"
        p_str, w_str = ratio_token.split("/")
        ratio = Fraction(int(p_str), int(w_str))
        if ratio > lam:
            nodes_index = parts.index("nodes")
            closure.update(int(token) - 1 for token in parts[nodes_index + 1:])
    return closure


def bppf_closure_at_lambda(pcf_bppf_oracle: Path, instance: Path, lam: Fraction) -> set[int]:
    n, _, _, _ = read_pcf(instance)
    with tempfile.TemporaryDirectory() as tmp:
        dimacs_path = Path(tmp) / "instance.dimacs"
        convert(instance, lam, dimacs_path)
        completed = subprocess.run(
            [str(pcf_bppf_oracle)], stdin=dimacs_path.open("r", encoding="utf-8"),
            check=True, text=True, capture_output=True,
        )
    closure: set[int] = set()
    for line in completed.stdout.splitlines():
        if not line.startswith("n "):
            continue
        _, node_id, breakpoint = line.split()
        node_id, breakpoint = int(node_id), int(breakpoint)
        if 2 <= node_id <= n + 1 and breakpoint <= 1:  # numParams == 1 always here
            closure.add(node_id - 2)
    return closure


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pcf-solve", type=Path, required=True)
    parser.add_argument("--pcf-bppf-oracle", type=Path, required=True)
    parser.add_argument("--instance", type=Path, required=True)
    parser.add_argument("--algorithm", default="hfma")
    parser.add_argument("--lambda-num", type=int, required=True)
    parser.add_argument("--lambda-den", type=int, required=True)
    arguments = parser.parse_args()
    lam = Fraction(arguments.lambda_num, arguments.lambda_den)

    ours = own_closure_at_lambda(arguments.pcf_solve, arguments.instance, arguments.algorithm, lam)
    theirs = bppf_closure_at_lambda(arguments.pcf_bppf_oracle, arguments.instance, lam)
    if ours == theirs:
        print(f"AGREE lambda={lam} |closure|={len(ours)}")
    else:
        print(f"MISMATCH lambda={lam}: ours has {len(ours - theirs)} extra, "
              f"BPPF has {len(theirs - ours)} extra", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
