#!/usr/bin/env python3
"""Statistics on the SIZE of the closure layers, i.e. how many vertices each
layer holds.

The benchmark CSVs record how many layers an instance has, not how big they
are, because the algorithms are timed and their output is discarded. That
distribution is worth knowing: it says whether the parametric solution is a
long chain of singletons or a few large blocks, which is what determines how
much work a peel step does. This tool runs pcf_solve on a sample of instances,
collects the layer sizes, and emits the summary table and the plot data used
by report/computational_report.tex.

Usage:
  python3 tools/layer_size_stats.py --pcf-solve build/pcf_solve \
      --instances instances/campaign_c --pattern 'gen_n10000_*_seed0.pcf' \
      --output-dir results/tables
"""
from __future__ import annotations

import argparse
import re
import statistics
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

RE_RANDOM = re.compile(r"^(?P<topo>gen|in|out)_n(?P<n>\d+)_rho(?P<rho>[0-9.]+)_"
                       r"(?P<family>[a-z-]+)_seed(?P<seed>\d+)")
RE_STRUCT = re.compile(r"^(?P<topo>path|binary|star)_n(?P<n>\d+)_"
                       r"(?P<family>[a-z-]+)_seed(?P<seed>\d+)")


def layer_sizes(pcf_solve: Path, instance: Path) -> list[int]:
    out = subprocess.run([str(pcf_solve), "--instance", str(instance),
                          "--algorithm", "hpac"],
                         check=True, text=True, capture_output=True).stdout
    sizes = []
    for line in out.splitlines():
        if not line.startswith("layer "):
            continue
        parts = line.split()
        sizes.append(len(parts) - parts.index("nodes") - 1)
    return sizes


def classify(name: str) -> dict:
    for regex in (RE_RANDOM, RE_STRUCT):
        m = regex.match(name)
        if m:
            info = m.groupdict()
            info.setdefault("rho", "--")
            return info
    return {"topo": "?", "n": "0", "rho": "--", "family": "?"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pcf-solve", type=Path, required=True)
    parser.add_argument("--instances", type=Path, action="append", required=True)
    parser.add_argument("--pattern", action="append", required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("results/tables"))
    args = parser.parse_args()

    per_group: dict[tuple[str, str], list[int]] = defaultdict(list)
    all_sizes: list[int] = []
    n_instances = 0
    for directory, pattern in zip(args.instances, args.pattern):
        for instance in sorted(directory.glob(pattern)):
            info = classify(instance.name)
            sizes = layer_sizes(args.pcf_solve, instance)
            if not sizes:
                continue
            n_instances += 1
            all_sizes += sizes
            per_group[(info["topo"], info["rho"])] += sizes
            per_group[("family:" + info["family"], "--")] += sizes
    if not all_sizes:
        raise SystemExit("no instance matched")

    def row(label: str, sizes: list[int]) -> list[str]:
        singletons = 100.0 * sum(1 for s in sizes if s == 1) / len(sizes)
        return [label, str(len(sizes)), f"{statistics.median(sizes):.0f}",
                f"{statistics.fmean(sizes):.2f}", str(max(sizes)),
                f"{singletons:.1f}"]

    header = ["group", "layers", "median", "mean", "max", "singletons (\\%)"]
    body = []
    for key in sorted(per_group):
        label = key[0] if key[1] == "--" else f"{key[0]}, $\\varrho={key[1]}$"
        label = label.replace("family:", "").replace("_", "-")
        body.append(row(f"\\texttt{{{label}}}", per_group[key]))

    lines = ["\\begin{tabular}{@{}lrrrrr@{}}", "\\toprule",
             " & ".join(header) + " \\\\", "\\midrule"]
    lines += [" & ".join(r) + " \\\\" for r in body]
    lines += ["\\bottomrule", "\\end{tabular}"]
    (args.output_dir / "rep_layer_sizes.tex").write_text("\n".join(lines) + "\n")

    # plot data: complementary cumulative distribution of the layer size
    counter = Counter(all_sizes)
    total = len(all_sizes)
    running = 0
    plot = ["size frac_at_least"]
    for size in sorted(counter):
        frac = 100.0 * (total - running) / total
        plot.append(f"{size} {frac:.4f}")
        running += counter[size]
    (args.output_dir / "rep_plotlayersize.dat").write_text("\n".join(plot) + "\n")

    print(f"instances={n_instances} layers={total} "
          f"median={statistics.median(all_sizes):.0f} "
          f"mean={statistics.fmean(all_sizes):.2f} max={max(all_sizes)} "
          f"singletons={100.0*sum(1 for s in all_sizes if s==1)/total:.1f}%")
    print(f"wrote {args.output_dir}/rep_layer_sizes.tex and rep_plotlayersize.dat")


if __name__ == "__main__":
    main()
