#!/usr/bin/env python3
"""Head-to-head race: HPaC vs Hochbaum's FULLY parametric HPF solver.

Both sides receive nothing but the instance and must produce the complete
optimal sequence of closure layers. This is the comparison the manuscript
wants: no probe values are computed by one method and handed to the other.

Reading the fully-parametric solver's output. It reports, per node, the
value of its `nodeBreakpoints` entry, which libhpf.c's addBreakpoint sets to
the parameter of the FIRST breakpoint at which the node is already in the
source set -- i.e. the UPPER bound of the first interval containing the
node, not the parameter at which it enters. Grouping nodes by that value and
ordering the groups therefore reproduces the closure layers in the right
order, but labels each group with the next group's parameter, and pushes the
final group onto the LAMBDA_HIGH sentinel. So we take only the PARTITION
from the solver and recompute every breakpoint ourselves, exactly, as
lambda_r = P(I_r)/W(I_r) -- which is what a breakpoint is (Section 1). No
floating-point value from the solver enters the comparison.

The solver runs on mu = -lambda (see tools/convert_to_fphpf.py), so its
group order in increasing mu is already the manuscript's order of decreasing
lambda.

Timing. The solver prints `t <read> <initialize> <solve>`; we take the solve
field, so input parsing and process start-up are excluded, matching the
convention already used for the simple-parametric comparison. HPaC is timed
in-process by pcf_benchmark over the same repetitions.
"""
from __future__ import annotations

import argparse
import csv
import statistics
import subprocess
import tempfile
from fractions import Fraction
from pathlib import Path

from convert_to_fphpf import convert, parse_output, read_pcf


def hpac_layers(pcf_solve: Path, instance: Path) -> list[tuple[Fraction, frozenset]]:
    """HPaC's own answer: (ratio, layer) in decreasing ratio order."""
    out = subprocess.run(
        [str(pcf_solve), "--instance", str(instance), "--algorithm", "hpac"],
        check=True, text=True, capture_output=True,
    ).stdout
    layers = []
    for line in out.splitlines():
        fields = line.split()
        if fields and fields[0] == "layer":
            num, den = fields[3].split("/")
            layers.append((Fraction(int(num), int(den)),
                           frozenset(int(v) for v in fields[5:])))
    return layers


def hpac_times_ns(pcf_benchmark: Path, instance: Path, repetitions: int) -> list[int]:
    completed = subprocess.run(
        [str(pcf_benchmark), "--instance", str(instance), "--algorithms", "hpac",
         "--repetitions", str(repetitions)],
        check=True, text=True, capture_output=True,
    )
    return [int(row["elapsed_ns"]) for row in csv.DictReader(completed.stdout.splitlines())]


def fphpf_layers(hpf_bin: Path, instance: Path, workdir: Path,
                 repetitions: int) -> tuple[list[frozenset], float]:
    """Run the fully parametric solver and return (layers, median solve seconds)."""
    dimacs = workdir / "race.in"
    out_file = workdir / "race.out"
    n, _ = convert(instance, dimacs)

    solve_times = []
    for _ in range(repetitions):
        subprocess.run([str(hpf_bin), str(dimacs), str(out_file)],
                       check=False, text=True, capture_output=True)
        _, threshold_mu, solve_seconds = parse_output(out_file, n)
        solve_times.append(solve_seconds)

    # Group vertices by reported value; increasing mu is decreasing lambda.
    grouped: dict[float, set] = {}
    for vertex, mu in threshold_mu.items():
        grouped.setdefault(mu, set()).add(vertex)
    layers = [frozenset(grouped[mu]) for mu in sorted(grouped)]
    return layers, statistics.median(solve_times)


def ratios_of(layers: list[frozenset], profit: list[int], weight: list[int]) -> list[Fraction]:
    return [Fraction(sum(profit[v] for v in layer), sum(weight[v] for v in layer))
            for layer in layers]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pcf-solve", type=Path, required=True)
    parser.add_argument("--pcf-benchmark", type=Path, required=True)
    parser.add_argument("--hpf", type=Path, required=True, help="fully parametric hpf binary")
    parser.add_argument("--instances", type=Path, nargs="+", required=True)
    # 11 repetitions is what the repository's official campaigns use; fewer
    # (e.g. 3) leaves HPaC's sub-millisecond runs cold and overstates its time
    # by up to 3x at n=100, which would understate the ratio.
    parser.add_argument("--repetitions", type=int, default=11)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    files = []
    for entry in args.instances:
        files.extend(sorted(entry.glob("*.pcf")) if entry.is_dir() else [entry])

    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        workdir = Path(tmp)
        for instance in files:
            n, profit, weight, _ = read_pcf(instance)
            ours = hpac_layers(args.pcf_solve, instance)
            theirs, hpf_seconds = fphpf_layers(args.hpf, instance, workdir, args.repetitions)

            # HPaC's node ids are 1-based in its printed output.
            our_sets = [frozenset(v - 1 for v in layer) for _, layer in ours]
            agree = our_sets == theirs
            their_ratios = ratios_of(theirs, profit, weight) if theirs else []
            ratios_agree = their_ratios == [ratio for ratio, _ in ours]

            hpac_ns = statistics.median(hpac_times_ns(args.pcf_benchmark, instance, args.repetitions))
            hpf_ns = hpf_seconds * 1e9
            rows.append({
                "instance": instance.name, "n": n,
                "layers_hpac": len(ours), "layers_fphpf": len(theirs),
                "same_partition": agree, "same_breakpoints": ratios_agree,
                "hpac_median_ns": int(hpac_ns), "fphpf_solve_median_ns": int(hpf_ns),
                "ratio_fphpf_over_hpac": round(hpf_ns / hpac_ns, 3) if hpac_ns else "",
            })
            flag = "" if agree else "  <== PARTITION MISMATCH"
            print(f"{instance.name} n={n} layers {len(ours)}/{len(theirs)} "
                  f"hpac={hpac_ns/1e6:.3f}ms fphpf={hpf_ns/1e6:.3f}ms "
                  f"x{rows[-1]['ratio_fphpf_over_hpac']}{flag}")

    if args.output:
        with args.output.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        print(f"\nwrote {args.output}")

    mismatches = [r for r in rows if not r["same_partition"]]
    print(f"\n{len(rows) - len(mismatches)}/{len(rows)} instances: identical closure-layer partition")
    if mismatches:
        print(f"{len(mismatches)} MISMATCHES: " + ", ".join(r["instance"] for r in mismatches[:10]))


if __name__ == "__main__":
    main()
