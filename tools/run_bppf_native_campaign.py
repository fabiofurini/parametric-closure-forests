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

Scope: unlike the single-lambda encoding, the native multi-lambda encoding's
exactness is bounded by instance SIZE, not just precision choice -- every
number gets multiplied by 10**prec inside BPPF before being stored as a
64-bit integer, so large instances (via convert_to_bppf_sequence.py's `big`
infinity-arc capacity) and/or a high `prec` (needed to resolve closely
spaced breakpoints) can together exceed exact double-precision integer
range. Instance/prec pairs past that bound are skipped with a printed
reason, not silently timed as if they were in scope.
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

import re

from convert_to_bppf_sequence import convert_sequence, closures_from_sequence_output, read_pcf


def hpac_layers(pcf_solve: Path, instance: Path) -> list:
    """Run HPaC once and parse its full layer sequence: a list of
    (ratio: Fraction, nodes: set[int]) in decreasing ratio order. Everything
    downstream (probes, per-probe reference closures) derives from this one
    parse — no repeated pcf_solve invocations."""
    completed = subprocess.run([str(pcf_solve), "--instance", str(instance), "--algorithm", "hpac"],
                                check=True, text=True, capture_output=True)
    layers = []
    for line in completed.stdout.splitlines():
        if not line.startswith("layer "):
            continue
        parts = line.split()
        p, w = parts[3].split("/")
        nodes = {int(token) - 1 for token in parts[parts.index("nodes") + 1:]}
        layers.append((Fraction(int(p), int(w)), nodes))
    return layers


def closure_at(layers: list, lam: Fraction) -> set:
    closure: set = set()
    for ratio, nodes in layers:
        if ratio > lam:
            closure.update(nodes)
    return closure


def time_ns(pcf_benchmark: Path, instance: Path, algorithm: str, repetitions: int,
            campaign_id: str) -> list[int]:
    completed = subprocess.run(
        [str(pcf_benchmark), "--instance", str(instance), "--algorithms", algorithm,
         "--repetitions", str(repetitions), "--campaign-id", campaign_id],
        check=True, text=True, capture_output=True,
    )
    return [int(row["elapsed_ns"]) for row in csv.DictReader(completed.stdout.splitlines())]


def v1_probes(ratios: list) -> list:
    """The v1 probe set (legacy hpf_compare.py, probe_parameters): one value
    below the smallest breakpoint, the midpoint of every consecutive pair,
    and one value above the largest — k+1 probes for k breakpoints, so the
    whole parametric solution (empty and full closure included) is
    certified in ONE BPPF process. Probes are returned in DECREASING order,
    matching the decreasing order of hpac_breakpoints' ratios: with this
    encoding's source-arc capacities max(0, p_i - lambda*w_i), a decreasing
    lambda sequence is what keeps source capacities non-decreasing, which
    BPPF's simple-parametric solver requires."""
    decreasing = sorted(ratios, reverse=True)
    gap_high = max(Fraction(1), abs(decreasing[0]) + 1)
    gap_low = max(Fraction(1), abs(decreasing[-1]) + 1)
    probes = [decreasing[0] + gap_high]
    probes += [(decreasing[i] + decreasing[i + 1]) / 2 for i in range(len(decreasing) - 1)]
    probes.append(decreasing[-1] - gap_low)
    return probes


def bppf_internal_ns(stdout: str) -> int:
    """BPPF's own cumulative solve timer: it prints 'Elapsed time: X' after
    each parameter, measured from one fixed start after input reading, so
    the maximum is the total native solve time (input parsing excluded) —
    the same quantity the v1 pipeline parsed."""
    elapsed = [float(m.group(1)) for m in re.finditer(r"Elapsed time:\s*([0-9.]+)", stdout)]
    return int(max(elapsed) * 1e9) if elapsed else -1


def check_agreement(layers: list, pcf_bppf_oracle: Path, instance: Path,
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
        if bppf_closures[j] == closure_at(layers, lam):
            continue
        # Probe j=0 sits above every breakpoint and probe j=k below every
        # one; probe j (1 <= j <= k-1) is the midpoint between the
        # decreasing ratios r_{j-1} and r_j, so the gaps that can explain a
        # tolerance merge at probe j are (j-1, j-1+1) and its neighbours.
        nearby = any(
            abs(ratios[i] - ratios[i + 1]) < tolerance_gap
            for i in (j - 1, j) if 0 <= i < len(ratios) - 1
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
        layers = hpac_layers(arguments.pcf_solve, instance)
        ratios = [ratio for ratio, _ in layers]
        if not ratios:
            print(f"skip {instance.name}: no layers")
            continue
        lambdas = v1_probes(ratios)

        with tempfile.TemporaryDirectory() as tmp:
            dimacs_path = Path(tmp) / "instance.dimacs"
            try:
                convert_sequence(instance, lambdas, arguments.prec, dimacs_path)
            except ValueError as error:
                print(f"skip {instance.name}: {error}")
                continue

            agrees, distinct_bppf = check_agreement(
                layers, arguments.pcf_bppf_oracle, instance, ratios, lambdas, dimacs_path, n,
                arguments.prec)

            bppf_times = []
            bppf_internal_times = []
            for _ in range(arguments.repetitions):
                started = time.perf_counter_ns()
                timed = subprocess.run([str(arguments.pcf_bppf)], stdin=dimacs_path.open("r", encoding="utf-8"),
                                        check=True, text=True, capture_output=True)
                bppf_times.append(time.perf_counter_ns() - started)
                bppf_internal_times.append(bppf_internal_ns(timed.stdout))

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
            "bppf_internal_median_ns": statistics.median(bppf_internal_times),
            "bppf_wall_median_ns": statistics.median(bppf_times),
        }
        rows.append(row)
        flag = "" if agrees else "  ** GENUINE DISAGREEMENT (not tolerance-explained), discard this row **"
        print(f"{instance.name}: n={n} hpac_breakpoints={len(ratios)} bppf_distinct={distinct_bppf} "
              f"hpac={row['hpac_median_ns']}ns bppf_internal={row['bppf_internal_median_ns']}ns "
              f"bppf_wall={row['bppf_wall_median_ns']}ns{flag}")

    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else [
        "instance", "n_nodes", "n_breakpoints_hpac", "n_probes", "n_breakpoints_bppf_distinct",
        "agrees_or_tolerance_explained", "hpac_median_ns", "bppf_internal_median_ns",
        "bppf_wall_median_ns",
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
