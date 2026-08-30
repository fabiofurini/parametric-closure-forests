#!/usr/bin/env python3
"""Native-speed comparison against BPPF: HPaC vs ONE pcf_bppf process per
instance, sweeping all of HPaC's breakpoints in a single call via
tools/convert_to_bppf_sequence.py's affine encoding -- unlike Campaign F
(tools/run_bppf_campaign.py), which is process-spawn-dominated by design
(one pcf_bppf_oracle process per breakpoint) and is a correctness oracle,
not a speed comparison. Do not run this campaign's encoding on an instance
without first validating it against HPaC with tools/validate_bppf_sequence.py
(same test-bed): a mismatch there means the timings collected here for that
instance are meaningless, not just imprecise.

Timing uses the plain `pcf_bppf` binary (no -DBREAKPOINTS: it doesn't pay
the cost of populating/printing the per-node breakpoint array, so its time
is the pure parametric-solve cost). Correctness/merge detection instead
uses `pcf_bppf_oracle` (-DBREAKPOINTS build) exactly ONCE per instance,
outside the timed region, reusing tools/validate_bppf_sequence.py's logic:
BPPF's own fixed-point arithmetic (precision `prec`, default 1e-6, same as
v1's methodology) can merge two HPaC breakpoints closer together than
10**-prec into one -- expected and reported per-instance via
n_breakpoints_bppf < n_breakpoints_hpac, never silently dropped.
"""
from __future__ import annotations

import argparse
import csv
import statistics
import subprocess
import tempfile
import time
from pathlib import Path

from fractions import Fraction

from convert_to_bppf import read_pcf
from convert_to_bppf_sequence import convert_sequence, closures_from_sequence_output
from run_bppf_campaign import hpac_breakpoints, midpoints, closure_from_hpac, time_ns


def check_agreement(pcf_solve: Path, pcf_bppf_oracle: Path, instance: Path,
                     ratios: list, lambdas: list, dimacs_path: Path, n: int, prec: int) -> tuple[bool, int]:
    """Returns (agrees_or_only_tolerance_explained_mismatches, n_distinct_breakpoints_bppf_saw).
    Same tolerance-vs-genuine classification as tools/validate_bppf_sequence.py:
    a mismatch is tolerance-explained if the two HPaC breakpoints flanking that
    probe are closer together than BPPF's fixed-point precision (10**-prec)."""
    completed = subprocess.run(
        [str(pcf_bppf_oracle)], stdin=dimacs_path.open("r", encoding="utf-8"),
        check=True, text=True, capture_output=True,
    )
    bppf_closures = closures_from_sequence_output(completed.stdout, n, len(lambdas))
    distinct = len({frozenset(c) for c in bppf_closures})
    tolerance_gap = Fraction(1, 10 ** prec)
    for j, lam in enumerate(lambdas):
        if bppf_closures[j] == closure_from_hpac(pcf_solve, instance, lam):
            continue
        nearby = any(
            abs(ratios[i] - ratios[i + 1]) < tolerance_gap
            for i in (j, j + 1) if 0 <= i < len(ratios) - 1
        )
        if not nearby:
            return False, distinct
    return True, distinct


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pcf-solve", type=Path, required=True)
    parser.add_argument("--pcf-benchmark", type=Path, required=True)
    parser.add_argument("--pcf-bppf", type=Path, required=True, help="plain build, no -DBREAKPOINTS")
    parser.add_argument("--pcf-bppf-oracle", type=Path, required=True, help="-DBREAKPOINTS build")
    parser.add_argument("--instances", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repetitions", type=int, default=5)
    parser.add_argument("--prec", type=int, default=6)
    arguments = parser.parse_args()

    rows: list[dict[str, object]] = []
    for instance in sorted(arguments.instances.glob("*.pcf")):
        n, _, _, _ = read_pcf(instance)
        ratios = hpac_breakpoints(arguments.pcf_solve, instance)
        lambdas = midpoints(ratios)
        if not lambdas:
            print(f"skip {instance.name}: fewer than 2 layers, nothing to probe")
            continue

        with tempfile.TemporaryDirectory() as tmp:
            dimacs_path = Path(tmp) / "instance.dimacs"
            convert_sequence(instance, lambdas, arguments.prec, dimacs_path)

            agrees, distinct_bppf = check_agreement(
                arguments.pcf_solve, arguments.pcf_bppf_oracle, instance, ratios, lambdas, dimacs_path, n,
                arguments.prec)

            bppf_times = []
            for _ in range(arguments.repetitions):
                started = time.perf_counter_ns()
                subprocess.run([str(arguments.pcf_bppf)], stdin=dimacs_path.open("r", encoding="utf-8"),
                                check=True, text=True, capture_output=True)
                bppf_times.append(time.perf_counter_ns() - started)

        hpac_times = time_ns(arguments.pcf_benchmark, instance, "hpac", arguments.repetitions,
                              "campaign_f_native")

        row = {
            "instance": instance.name,
            "n_nodes": n,
            "n_breakpoints_hpac": len(ratios),
            "n_probes": len(lambdas),
            "n_breakpoints_bppf_distinct": distinct_bppf,
            "agrees_or_tolerance_explained": agrees,
            "hpac_median_ns": statistics.median(hpac_times),
            "bppf_native_median_ns": statistics.median(bppf_times),
        }
        rows.append(row)
        flag = "" if agrees else "  ** GENUINE DISAGREEMENT (not tolerance-explained), discard this row **"
        print(f"{instance.name}: n={n} hpac_breakpoints={len(ratios)} bppf_distinct={distinct_bppf} "
              f"hpac={row['hpac_median_ns']}ns bppf_native={row['bppf_native_median_ns']}ns{flag}")

    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else [
        "instance", "n_nodes", "n_breakpoints_hpac", "n_probes", "n_breakpoints_bppf_distinct",
        "agrees_or_tolerance_explained", "hpac_median_ns", "bppf_native_median_ns",
    ]
    with arguments.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {arguments.output} ({len(rows)} instances)")

    disagreements = sum(1 for row in rows if not row["agrees_or_tolerance_explained"])
    if disagreements:
        print(f"WARNING: {disagreements} instance(s) disagree with HPaC -- their timings are not meaningful, "
              "re-run tools/validate_bppf_sequence.py on them before trusting this campaign")


if __name__ == "__main__":
    main()
