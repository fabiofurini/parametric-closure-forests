#!/usr/bin/env python3
"""Validate tools/convert_to_bppf_sequence.py's multi-lambda affine encoding
against HPaC before trusting any timing numbers from it (plan: BPPF
native-speed comparison). For each instance:

1. get HPaC's exact breakpoints and build probe lambdas (midpoints, same
   scheme as tools/run_bppf_campaign.py);
2. call the new sequence converter ONCE with all probes, run pcf_bppf_oracle
   ONCE, and reconstruct one closure per probe from its output;
3. compare each probe's BPPF closure against HPaC's closure at that lambda
   (tools/run_bppf_campaign.py::closure_from_hpac);
4. classify every mismatch as tolerance-driven (two HPaC breakpoints closer
   together than 10**-prec, so BPPF's fixed-point arithmetic could not tell
   the corresponding probes apart -- expected, per docs/EXPERIMENTAL_PROTOCOL.md
   once written up) or genuine (anything else -- this must be zero before the
   encoding is trusted for the native-speed campaign).
"""
from __future__ import annotations

import argparse
import subprocess
import tempfile
from fractions import Fraction
from pathlib import Path

from convert_to_bppf_sequence import convert_sequence, closures_from_sequence_output
from run_bppf_campaign import hpac_breakpoints, midpoints, closure_from_hpac


def validate_instance(pcf_solve: Path, pcf_bppf_oracle: Path, instance: Path, prec: int) -> tuple[int, int, int]:
    """Returns (n_probes, tolerance_mismatches, genuine_mismatches)."""
    from convert_to_bppf import read_pcf
    n, _, _, _ = read_pcf(instance)

    ratios = hpac_breakpoints(pcf_solve, instance)
    lambdas = midpoints(ratios)
    if not lambdas:
        return 0, 0, 0

    with tempfile.TemporaryDirectory() as tmp:
        dimacs_path = Path(tmp) / "instance.dimacs"
        convert_sequence(instance, lambdas, prec, dimacs_path)
        completed = subprocess.run(
            [str(pcf_bppf_oracle)], stdin=dimacs_path.open("r", encoding="utf-8"),
            check=True, text=True, capture_output=True,
        )
    bppf_closures = closures_from_sequence_output(completed.stdout, n, len(lambdas))

    tolerance_gap = Fraction(1, 10 ** prec)
    tolerance_mismatches = 0
    genuine_mismatches = 0
    for j, lam in enumerate(lambdas):
        expected = closure_from_hpac(pcf_solve, instance, lam)
        actual = bppf_closures[j]
        if actual == expected:
            continue
        # is this probe adjacent (in the breakpoint list) to another
        # breakpoint closer than the fixed-point precision allows to
        # resolve?
        nearby = any(
            abs(ratios[i] - ratios[i + 1]) < tolerance_gap
            for i in (j, j + 1) if 0 <= i < len(ratios) - 1
        )
        if nearby:
            tolerance_mismatches += 1
        else:
            genuine_mismatches += 1
            print(f"  GENUINE mismatch on {instance.name} at probe {j} (lambda={lam}): "
                  f"expected {sorted(expected)}, got {sorted(actual)}")
    return len(lambdas), tolerance_mismatches, genuine_mismatches


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pcf-solve", type=Path, required=True)
    parser.add_argument("--pcf-bppf-oracle", type=Path, required=True)
    parser.add_argument("--instances", type=Path, required=True)
    parser.add_argument("--prec", type=int, default=6)
    arguments = parser.parse_args()

    total_probes = total_tolerance = total_genuine = 0
    instances_with_genuine = 0
    for instance in sorted(arguments.instances.glob("*.pcf")):
        probes, tolerance, genuine = validate_instance(
            arguments.pcf_solve, arguments.pcf_bppf_oracle, instance, arguments.prec)
        total_probes += probes
        total_tolerance += tolerance
        total_genuine += genuine
        if genuine:
            instances_with_genuine += 1
        status = "OK" if genuine == 0 else "GENUINE MISMATCH"
        print(f"{instance.name}: probes={probes} tolerance_merges={tolerance} genuine={genuine} [{status}]")

    print()
    print(f"TOTAL: probes={total_probes} tolerance_merges={total_tolerance} "
          f"genuine_mismatches={total_genuine} instances_with_genuine={instances_with_genuine}")
    if total_genuine:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
