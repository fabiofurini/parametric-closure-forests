#!/usr/bin/env python3
"""Campaign F: BPPF general parametric-flow baseline (plan section 9.6),
scope-limited per docs/EXPERIMENTAL_PROTOCOL.md.

For every instance, this script:

1. gets the exact breakpoint sequence from our own HPaC solve;
2. times HPaC and RaC end-to-end (they compute the whole sequence in one
   call each) via pcf_benchmark;
3. times BPPF's total cost to recover the SAME sequence the only way its
   single-lambda reduction supports: one pcf_bppf_oracle process per
   breakpoint midpoint, each timed with Python's perf_counter and summed;
4. cross-checks, for every sampled midpoint, that BPPF's minimum-cut closure
   agrees with HPaC's closure at that lambda (reusing the same Oracle-2
   machinery as tools/verify_with_bppf.py), and records any mismatch.

The BPPF total time is one Python-process-spawn-dominated number, not a
native parametric solve; docs/EXPERIMENTAL_PROTOCOL.md explains why this
campaign stays scoped to small/medium instances and is reported with that
caveat attached, never silently merged into the HPaC/RaC comparison tables.
"""
from __future__ import annotations

import argparse
import csv
import statistics
import subprocess
import tempfile
import time
from fractions import Fraction
from pathlib import Path

from convert_to_bppf import convert, read_pcf


def hpac_breakpoints(pcf_solve: Path, instance: Path) -> list[Fraction]:
    completed = subprocess.run([str(pcf_solve), "--instance", str(instance), "--algorithm", "hpac"],
                                check=True, text=True, capture_output=True)
    ratios: list[Fraction] = []
    for line in completed.stdout.splitlines():
        if line.startswith("layer "):
            token = line.split()[3]
            p, w = token.split("/")
            ratios.append(Fraction(int(p), int(w)))
    return ratios


def midpoints(ratios: list[Fraction]) -> list[Fraction]:
    return [(ratios[i] + ratios[i + 1]) / 2 for i in range(len(ratios) - 1)]


def closure_from_bppf_output(stdout: str, n: int) -> set[int]:
    closure: set[int] = set()
    for line in stdout.splitlines():
        if not line.startswith("n "):
            continue
        _, node_id, breakpoint = line.split()
        node_id, breakpoint = int(node_id), int(breakpoint)
        if 2 <= node_id <= n + 1 and breakpoint <= 1:
            closure.add(node_id - 2)
    return closure


def closure_from_hpac(pcf_solve: Path, instance: Path, lam: Fraction) -> set[int]:
    completed = subprocess.run([str(pcf_solve), "--instance", str(instance), "--algorithm", "hpac"],
                                check=True, text=True, capture_output=True)
    closure: set[int] = set()
    for line in completed.stdout.splitlines():
        if not line.startswith("layer "):
            continue
        parts = line.split()
        p, w = parts[3].split("/")
        if Fraction(int(p), int(w)) > lam:
            closure.update(int(token) - 1 for token in parts[parts.index("nodes") + 1:])
    return closure


def time_bppf_total(pcf_bppf_oracle: Path, instance: Path, lambdas: list[Fraction], n: int) -> tuple[int, int]:
    total_ns = 0
    mismatches = 0
    with tempfile.TemporaryDirectory() as tmp:
        for lam in lambdas:
            dimacs_path = Path(tmp) / "instance.dimacs"
            convert(instance, lam, dimacs_path)
            started = time.perf_counter_ns()
            completed = subprocess.run([str(pcf_bppf_oracle)], stdin=dimacs_path.open("r", encoding="utf-8"),
                                        check=True, text=True, capture_output=True)
            total_ns += time.perf_counter_ns() - started
            bppf_closure = closure_from_bppf_output(completed.stdout, n)
            expected = closure_from_hpac_cached.get((instance, lam))
            if expected is not None and bppf_closure != expected:
                mismatches += 1
    return total_ns, mismatches


closure_from_hpac_cached: dict[tuple[Path, Fraction], set[int]] = {}


def time_ns(pcf_benchmark: Path, instance: Path, algorithm: str, repetitions: int, campaign_id: str) -> list[int]:
    completed = subprocess.run(
        [str(pcf_benchmark), "--instance", str(instance), "--algorithms", algorithm,
         "--repetitions", str(repetitions), "--campaign-id", campaign_id],
        check=True, text=True, capture_output=True,
    )
    return [int(row["elapsed_ns"]) for row in csv.DictReader(completed.stdout.splitlines())]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pcf-solve", type=Path, required=True)
    parser.add_argument("--pcf-benchmark", type=Path, required=True)
    parser.add_argument("--pcf-bppf-oracle", type=Path, required=True)
    parser.add_argument("--instances", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--max-breakpoints", type=int, default=200,
                         help="skip instances whose HPaC sequence has more sampled midpoints than this "
                              "(one BPPF process per midpoint makes this campaign process-spawn-bound)")
    arguments = parser.parse_args()

    rows: list[dict[str, object]] = []
    for instance in sorted(arguments.instances.glob("*.pcf")):
        n, _, _, _ = read_pcf(instance)
        ratios = hpac_breakpoints(arguments.pcf_solve, instance)
        lambdas = midpoints(ratios)
        if len(lambdas) > arguments.max_breakpoints:
            print(f"skip {instance.name}: {len(lambdas)} midpoints exceeds --max-breakpoints")
            continue
        for lam in lambdas:
            closure_from_hpac_cached[(instance, lam)] = closure_from_hpac(arguments.pcf_solve, instance, lam)

        hpac_times = time_ns(arguments.pcf_benchmark, instance, "hpac", arguments.repetitions, "campaign_f")
        rac_times = time_ns(arguments.pcf_benchmark, instance, "rac", arguments.repetitions, "campaign_f")
        bppf_totals = []
        mismatch_total = 0
        for _ in range(arguments.repetitions):
            total_ns, mismatches = time_bppf_total(arguments.pcf_bppf_oracle, instance, lambdas, n)
            bppf_totals.append(total_ns)
            mismatch_total += mismatches

        row = {
            "instance": instance.name,
            "n_nodes": n,
            "n_breakpoints_sampled": len(lambdas),
            "hpac_median_ns": statistics.median(hpac_times),
            "rac_median_ns": statistics.median(rac_times),
            "bppf_median_total_ns": statistics.median(bppf_totals),
            "bppf_mismatches": mismatch_total,
        }
        rows.append(row)
        print(f"{instance.name}: n={n} breakpoints={len(lambdas)} "
              f"hpac={row['hpac_median_ns']}ns rac={row['rac_median_ns']}ns "
              f"bppf_total={row['bppf_median_total_ns']}ns mismatches={mismatch_total}")

    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    with arguments.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()) if rows else
                                 ["instance", "n_nodes", "n_breakpoints_sampled", "hpac_median_ns",
                                  "rac_median_ns", "bppf_median_total_ns", "bppf_mismatches"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {arguments.output} ({len(rows)} instances)")


if __name__ == "__main__":
    main()
