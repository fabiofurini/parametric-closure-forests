#!/usr/bin/env python3
"""Statistics on the FOREST structure of the instances: how many trees each
generated forest contains and how big those trees are.

The benchmark CSVs record the number of arcs and of connected components, but
not the distribution of the component sizes. That distribution is the reason
density is an experimental factor: RaC pays a per-component overhead, while the
peeling algorithms do not care how the vertices are split, so knowing whether a
sparse forest is "many small trees" or "one big tree plus dust" is needed to
read Section 8.2 of the report. This tool reads the .pcf files directly (no
solver involved, the structure is in the arc list) and emits the tables and
plot data used by report/computational_report.tex.

Usage:
  python3 tools/forest_structure_stats.py \
      --group 'mixed-forest,instances/campaign_c,gen_n100000_rho*_independent-positive_seed*.pcf' \
      --output-dir results/tables
"""
from __future__ import annotations

import argparse
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path

RE_NAME = re.compile(r"^(?P<topo>gen|in|out|path|binary|star)_n(?P<n>\d+)"
                     r"(?:_rho(?P<rho>[0-9.]+))?_")


def read_forest(path: Path) -> tuple[int, list[tuple[int, int]]]:
    n = 0
    arcs: list[tuple[int, int]] = []
    expected = 0
    with path.open() as handle:
        for line in handle:
            if line.startswith("n "):
                n = int(line.split()[1])
            elif line.startswith("arcs"):
                expected = int(line.split()[1])
            elif line[:1].isdigit() and expected:
                u, v = line.split()
                # .pcf vertex ids are 1-based (see src/instance.cpp)
                arcs.append((int(u) - 1, int(v) - 1))
    return n, arcs


def component_sizes(n: int, arcs: list[tuple[int, int]]) -> list[int]:
    """Sizes of the connected components of the UNDERLYING undirected graph:
    that is what "one tree of the forest" means, independently of the arc
    orientations."""
    parent = list(range(n))

    def find(x: int) -> int:
        root = x
        while parent[root] != root:
            root = parent[root]
        while parent[x] != root:            # path compression
            parent[x], x = root, parent[x]
        return root

    for u, v in arcs:
        ru, rv = find(u), find(v)
        if ru != rv:
            parent[ru] = rv
    sizes = Counter(find(v) for v in range(n))
    return sorted(sizes.values(), reverse=True)


def fmt(value: float) -> str:
    return f"{value:,.0f}".replace(",", "\\,")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--group", action="append", required=True,
                        help="label,directory,glob")
    parser.add_argument("--output-dir", type=Path, default=Path("results/tables"))
    parser.add_argument("--ccdf-group", default="mixed-forest",
                        help="label whose largest size gets the CCDF plot")
    args = parser.parse_args()

    # key -> list of (n, arcs, sizes) per instance
    per_key: dict[tuple[str, int, str], list[tuple[int, int, list[int]]]] = \
        defaultdict(list)
    for spec in args.group:
        label, directory, glob = spec.split(",", 2)
        for path in sorted(Path(directory).glob(glob)):
            match = RE_NAME.match(path.name)
            if not match:
                continue
            rho = match.group("rho") or "--"
            n, arcs = read_forest(path)
            per_key[(label, int(match.group("n")), rho)].append(
                (n, len(arcs), component_sizes(n, arcs)))
    if not per_key:
        raise SystemExit("no instance matched")

    def med(values) -> float:
        return statistics.median(values)

    # This table is shown full width with its plot below it (report macro
    # \tabfigwide), so it can afford every column.
    header = ["class, $n$", "$\\varrho$", "\\#inst", "arcs", "\\#trees",
              "trees$/n$", "median", "mean", "largest", "\\% of $n$",
              "isolated (\\%)"]
    rows = []
    for key in sorted(per_key, key=lambda k: (k[0], k[1], k[2])):
        label, n, rho = key
        data = per_key[key]
        trees = [len(sizes) for _, _, sizes in data]
        arcs = [a for _, a, _ in data]
        allsizes = [s for _, _, sizes in data for s in sizes]
        largest = [sizes[0] for _, _, sizes in data]
        isolated = [100.0 * sum(1 for s in sizes if s == 1) / len(sizes)
                    for _, _, sizes in data]
        exponent = {1000: "10^3", 10000: "10^4", 100000: "10^5"}.get(n, str(n))
        short = label.replace("-forest", "").replace("-mixed", "")
        rows.append([
            f"\\texttt{{{short}}}, $" + exponent + "$",
            rho if rho != "--" else "--", str(len(data)),
            fmt(med(arcs)), fmt(med(trees)),
            f"{med(trees) / n:.3f}",
            fmt(med(allsizes)),
            f"{statistics.fmean(allsizes):,.1f}".replace(",", "\\,"),
            fmt(med(largest)),
            f"{100.0 * med(largest) / n:.1f}",
            f"{med(isolated):.1f}",
        ])

    lines = ["\\begin{tabular}{@{}l" + "r" * (len(header) - 1) + "@{}}",
             "\\toprule", " & ".join(header) + " \\\\", "\\midrule"]
    previous = None
    for row, key in zip(rows, sorted(per_key, key=lambda k: (k[0], k[1], k[2]))):
        if previous is not None and key[0] != previous:
            lines.append("\\midrule")
        previous = key[0]
        lines.append(" & ".join(row) + " \\\\")
    lines += ["\\bottomrule", "\\end{tabular}"]
    (args.output_dir / "rep_forest_struct.tex").write_text("\n".join(lines) + "\n")

    # ---- plot 1: how the structure moves with the density, at the largest n
    ccdf_keys = [k for k in per_key if k[0] == args.ccdf_group and k[2] != "--"]
    if ccdf_keys:
        biggest = max(k[1] for k in ccdf_keys)
        keys = sorted((k for k in ccdf_keys if k[1] == biggest),
                      key=lambda k: float(k[2]))
        plot = ["rho trees mean max largest"]
        for key in keys:
            data = per_key[key]
            allsizes = [s for _, _, sizes in data for s in sizes]
            plot.append(f"{key[2]} {med([len(s) for _, _, s in data]):.0f} "
                        f"{statistics.fmean(allsizes):.3f} "
                        f"{max(sizes[0] for _, _, sizes in data)} "
                        f"{med([sizes[0] for _, _, sizes in data]):.0f}")
        (args.output_dir / "rep_plotforest.dat").write_text("\n".join(plot) + "\n")

        # ---- plot 2: CCDF of the tree size, one curve per density
        grid = sorted({int(round(1.15 ** e)) for e in range(0, 110)}
                      | {1, 2, 3, 5, 10})
        grid = [s for s in grid if s <= biggest]
        curves = {}
        for key in keys:
            allsizes = sorted(s for _, _, sizes in per_key[key] for s in sizes)
            total = len(allsizes)
            counter = Counter(allsizes)
            cum, at_least = 0, {}
            for size in sorted(counter):
                at_least[size] = 100.0 * (total - cum) / total
                cum += counter[size]
            last = 100.0
            column = []
            for size in grid:
                for present in sorted(at_least):
                    if present >= size:
                        last = at_least[present]
                        break
                else:
                    last = 0.0
                column.append(last)
            curves[key[2]] = column
        names = [f"r{k[2].replace('.', '')}" for k in keys]
        plot = ["size " + " ".join(names)]
        for index, size in enumerate(grid):
            values = [curves[k[2]][index] for k in keys]
            if all(v == 0.0 for v in values):
                continue
            plot.append(f"{size} " + " ".join(f"{v:.4f}" for v in values))
        (args.output_dir / "rep_plotforestccdf.dat").write_text(
            "\n".join(plot) + "\n")

        # ---- the same distribution as a table, at selected sizes
        marks = [s for s in (1, 2, 3, 5, 10, 100, 1000, 10000) if s <= biggest]
        head = ["$s$"] + [f"$\\varrho={k[2]}$" for k in keys]
        body = []
        for size in marks:
            cells = []
            for key in keys:
                index = min(range(len(grid)), key=lambda i: abs(grid[i] - size))
                value = curves[key[2]][index]
                cells.append(f"{value:.2f}" if value >= 0.01 else
                             ("$<0.01$" if value > 0 else "0"))
            body.append([fmt(size)] + cells)
        largest_row = ["largest tree"] + [
            fmt(max(sizes[0] for _, _, sizes in per_key[key])) for key in keys]
        inst_row = ["\\#inst"] + [str(len(per_key[key])) for key in keys]
        span = len(keys)
        lines = ["\\begin{tabular}{@{}r" + "r" * span + "@{}}", "\\toprule",
                 " & " + f"\\multicolumn{{{span}}}{{c}}"
                 "{\\% of trees with size $\\ge s$} \\\\",
                 f"\\cmidrule(l){{2-{span + 1}}}",
                 " & ".join(head) + " \\\\", "\\midrule"]
        lines += [" & ".join(r) + " \\\\" for r in body]
        lines += ["\\midrule", " & ".join(largest_row) + " \\\\",
                  " & ".join(inst_row) + " \\\\",
                  "\\bottomrule", "\\end{tabular}"]
        (args.output_dir / "rep_forest_ccdf.tex").write_text(
            "\n".join(lines) + "\n")

    print(f"groups={len(per_key)} "
          f"instances={sum(len(v) for v in per_key.values())}")
    for key in sorted(per_key, key=lambda k: (k[0], k[1], k[2])):
        data = per_key[key]
        allsizes = [s for _, _, sizes in data for s in sizes]
        print(f"  {key}: inst={len(data)} trees={med([len(s) for _,_,s in data]):.0f} "
              f"median_size={med(allsizes):.0f} mean={statistics.fmean(allsizes):.2f} "
              f"max={max(sizes[0] for _,_,sizes in data)}")
    print(f"wrote {args.output_dir}/rep_forest_struct.tex, "
          f"rep_plotforest.dat, rep_plotforestccdf.dat")


if __name__ == "__main__":
    main()
