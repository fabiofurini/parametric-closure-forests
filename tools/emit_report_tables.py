#!/usr/bin/env python3
"""Emit the detailed LaTeX table fragments used by report/computational_report.tex.

tools/emit_latex_tables.py produces the summary fragments cited by the
manuscript (one ratio per size). The technical report goes further: it breaks
every campaign down by coefficient family and by density, and reports absolute
times per algorithm side by side. Those breakdowns are generated here, from
results/processed/processed.csv only, so no number in the report is hand-typed.

Every fragment is a bare `tabular` (booktabs rules), to be \\input inside a
table/figure environment that supplies its own caption -- same convention as
tools/emit_latex_tables.py.
"""
from __future__ import annotations

import argparse
import csv
import statistics
from collections import defaultdict
from pathlib import Path

MS = 1e6  # nanoseconds -> milliseconds

NICE = {"pac": "PaC", "dpac": "DPaC", "hpac": "HPaC", "dhpac": "DHPaC",
        "hipac": "HIPaC", "hopac": "HOPaC", "rac": "RaC"}


def load(processed: Path) -> list[dict]:
    with processed.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def fmt(value: float) -> str:
    """One decimal, thousands separated by a thin space -- as in the manuscript."""
    text = f"{value:,.1f}".replace(",", "\\,")
    return text


def tabular(header: list[str], rows: list[list[str]], align: str,
            group: tuple[str, int, int] | None = None) -> str:
    out = ["\\begin{tabular}{@{}" + align + "@{}}", "\\toprule"]
    if group is not None:
        label, first, last = group
        span = last - first + 1
        lead = " & " * (first - 1)
        out.append(lead + f"\\multicolumn{{{span}}}{{c}}{{{label}}} \\\\")
        out.append(f"\\cmidrule(l){{{first}-{last}}}")
    out.append(" & ".join(header) + " \\\\")
    out.append("\\midrule")
    out += [" & ".join(r) + " \\\\" for r in rows]
    out += ["\\bottomrule", "\\end{tabular}"]
    return "\n".join(out) + "\n"


def median_times(rows, campaign, algorithms, key):
    """median elapsed time (ms) per (key value, algorithm)."""
    acc = defaultdict(list)
    for r in rows:
        if r["campaign_id"] != campaign or r["algorithm"] not in algorithms:
            continue
        acc[(r[key], r["algorithm"])].append(float(r["median_elapsed_ns"]) / MS)
    return acc


def paired_ratio(rows, campaign, numerator, denominator, key):
    """median and IQR of the per-instance ratio, grouped by `key`."""
    per_instance = defaultdict(dict)
    meta = {}
    for r in rows:
        if r["campaign_id"] != campaign:
            continue
        ident = (r["instance"],)
        per_instance[ident][r["algorithm"]] = float(r["median_elapsed_ns"])
        meta[ident] = r[key]
    acc = defaultdict(list)
    for ident, byalg in per_instance.items():
        if numerator in byalg and denominator in byalg:
            acc[meta[ident]].append(byalg[numerator] / byalg[denominator])
    return acc


def sort_key(value: str):
    try:
        return (0, float(value))
    except ValueError:
        return (1, value)


def write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")
    print(f"wrote {path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--processed", type=Path,
                        default=Path("results/processed/processed.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("results/tables"))
    args = parser.parse_args()
    rows = load(args.processed)
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)

    # ---- absolute times per algorithm, by size, one file per campaign ----
    for campaign, algorithms in [
        ("campaign_b", ["pac", "dpac", "hpac", "dhpac", "rac"]),
        ("campaign_c", ["hpac", "dhpac", "rac"]),
        ("campaign_d_path", ["pac", "hpac", "dhpac", "rac"]),
        ("campaign_d_binary", ["pac", "hpac", "dhpac", "rac"]),
        ("campaign_d_star", ["pac", "hpac", "dhpac", "rac"]),
        ("campaign_e_in", ["hpac", "dhpac", "hipac", "rac"]),
        ("campaign_e_out", ["hpac", "dhpac", "hopac", "rac"]),
    ]:
        acc = median_times(rows, campaign, algorithms, "n_nodes")
        sizes = sorted({int(k[0]) for k in acc}, key=int)
        body = []
        for n in sizes:
            cells = [fmt(statistics.median(acc[(str(n), a)])) if (str(n), a) in acc else "--"
                     for a in algorithms]
            body.append([fmt(n).replace(".0", ""), *cells])
        head = ["$n$"] + [f"\\texttt{{{NICE[a]}}}" for a in algorithms]
        write(out / f"rep_times_{campaign}.tex",
              tabular(head, body, "r" + "r" * len(algorithms),
                      group=("CPU time (ms)", 2, len(algorithms) + 1)))

    # ---- breakdown by coefficient family and by density, every campaign ----
    # (the structured families have no density parameter, hence family only)
    for campaign, algorithms, keys in [
        ("campaign_b", ["pac", "hpac", "rac"], ["coefficient_class", "rho"]),
        ("campaign_c", ["hpac", "dhpac", "rac"], ["coefficient_class", "rho"]),
        ("campaign_e_in", ["hpac", "hipac", "rac"], ["coefficient_class", "rho"]),
        ("campaign_e_out", ["hpac", "hopac", "rac"], ["coefficient_class", "rho"]),
        ("campaign_d_path", ["pac", "hpac", "rac"], ["coefficient_class"]),
        ("campaign_d_binary", ["pac", "hpac", "rac"], ["coefficient_class"]),
        ("campaign_d_star", ["pac", "hpac", "rac"], ["coefficient_class"]),
    ]:
        for key in keys:
            name = "family" if key == "coefficient_class" else "rho"
            acc = median_times(rows, campaign, algorithms, key)
            keys = sorted({k[0] for k in acc}, key=sort_key)
            body = []
            for value in keys:
                cells = [fmt(statistics.median(acc[(value, a)])) if (value, a) in acc else "--"
                         for a in algorithms]
                label = f"\\texttt{{{value}}}" if name == "family" else value
                body.append([label, *cells])
            head = ["family" if name == "family" else "$\\varrho$"] + \
                   [f"\\texttt{{{NICE[a]}}}" for a in algorithms]
            align = ("l" if name == "family" else "r") + "r" * len(algorithms)
            write(out / f"rep_times_{campaign}_by_{name}.tex",
                  tabular(head, body, align,
                          group=("median CPU time (ms)", 2, len(algorithms) + 1)))

    # ---- paired ratios broken down by family (the manuscript only has by size) ----
    for campaign, num, den in [("campaign_b", "rac", "hpac"),
                               ("campaign_c", "rac", "hpac"),
                               ("campaign_b", "pac", "hpac"),
                               ("campaign_e_in", "hipac", "hpac"),
                               ("campaign_e_out", "hopac", "hpac"),
                               ("campaign_e_in", "rac", "hpac"),
                               ("campaign_e_out", "rac", "hpac"),
                               ("campaign_d_path", "rac", "hpac"),
                               ("campaign_d_binary", "rac", "hpac"),
                               ("campaign_d_star", "rac", "hpac"),
                               ("campaign_d_star", "rac", "pac")]:
        acc = paired_ratio(rows, campaign, num, den, "coefficient_class")
        if not acc:
            continue
        body = []
        for value in sorted(acc, key=sort_key):
            values = acc[value]
            quart = statistics.quantiles(values, n=4, method="inclusive") if len(values) > 3 else None
            iqr = f"{quart[2] - quart[0]:.3f}" if quart else "--"
            body.append([f"\\texttt{{{value}}}", str(len(values)),
                         f"{statistics.median(values):.3f}", iqr])
        head = ["family", "\\#inst", f"median \\texttt{{{NICE[num]}}}/\\texttt{{{NICE[den]}}}", "IQR"]
        write(out / f"rep_ratio_{campaign}_{num}_over_{den}_by_family.tex",
              tabular(head, body, "lrrr"))

    # ---- plot data: one .dat per campaign, pgfplots reads it with \addplot table ----
    for campaign, algorithms in [
        ("campaign_b", ["pac", "dpac", "hpac", "dhpac", "rac"]),
        ("campaign_c", ["hpac", "dhpac", "rac"]),
        ("campaign_d_path", ["pac", "hpac", "rac"]),
        ("campaign_d_binary", ["pac", "hpac", "rac"]),
        ("campaign_d_star", ["pac", "hpac", "rac"]),
        ("campaign_e_in", ["hpac", "hipac", "rac"]),
        ("campaign_e_out", ["hpac", "hopac", "rac"]),
    ]:
        acc = median_times(rows, campaign, algorithms, "n_nodes")
        sizes = sorted({int(k[0]) for k in acc})
        lines = ["n " + " ".join(algorithms)]
        for n in sizes:
            cells = []
            for a in algorithms:
                key = (str(n), a)
                cells.append(f"{statistics.median(acc[key]):.4f}" if key in acc else "nan")
            lines.append(f"{n} " + " ".join(cells))
        write(out / f"rep_plot_{campaign}.dat", "\n".join(lines) + "\n")

    # ---- instance structure actually generated, by density (campaign C) ----
    struct = defaultdict(lambda: defaultdict(list))
    for r in rows:
        if r["campaign_id"] == "campaign_c" and r["algorithm"] == "hpac":
            struct[r["rho"]]["arcs"].append(int(r["n_arcs"]))
            struct[r["rho"]]["comp"].append(int(r["n_components"]))
            struct[r["rho"]]["layers"].append(int(r["n_layers"]))
    body = []
    for rho in sorted(struct, key=sort_key):
        d = struct[rho]
        body.append([rho, f"{statistics.median(d['arcs']):.0f}",
                     f"{statistics.median(d['comp']):.0f}",
                     f"{statistics.median(d['layers']):.0f}"])
    write(out / "rep_struct_by_rho.tex",
          tabular(["$\\varrho$", "arcs", "components", "closure layers"],
                  body, "rrrr", group=("median over campaign C", 2, 4)))

    # ---- closure layers by size, both random campaigns ----
    lay = defaultdict(list)
    for r in rows:
        if r["campaign_id"] in ("campaign_b", "campaign_c") and r["algorithm"] == "hpac":
            lay[int(r["n_nodes"])].append(int(r["n_layers"]))
    body = [[fmt(n).replace(".0", ""), f"{statistics.median(lay[n]):.0f}",
             f"{min(lay[n])}", f"{max(lay[n])}"] for n in sorted(lay)]
    write(out / "rep_layers_by_size.tex",
          tabular(["$n$", "median", "min", "max"], body, "rrrr",
                  group=("\\# closure layers", 2, 4)))

    # ---- dispersion of the absolute times: relative IQR ----
    for campaign, algorithms in [("campaign_c", ["hpac", "dhpac", "rac"]),
                                 ("campaign_e_in", ["hpac", "hipac", "rac"])]:
        acc = defaultdict(list)
        for r in rows:
            if r["campaign_id"] == campaign and r["algorithm"] in algorithms:
                med = float(r["median_elapsed_ns"])
                if med > 0:
                    acc[(int(r["n_nodes"]), r["algorithm"])].append(
                        100.0 * float(r["iqr_elapsed_ns"]) / med)
        sizes = sorted({k[0] for k in acc})
        body = []
        for n in sizes:
            body.append([fmt(n).replace(".0", "")] +
                        [f"{statistics.median(acc[(n, a)]):.1f}" if (n, a) in acc else "--"
                         for a in algorithms])
        write(out / f"rep_iqr_{campaign}.tex",
              tabular(["$n$"] + [f"\\texttt{{{NICE[a]}}}" for a in algorithms],
                      body, "r" + "r" * len(algorithms),
                      group=("median relative IQR of the timing (\\%)", 2,
                             len(algorithms) + 1)))

    # ---- family x size detail for the two headline algorithms ----
    for campaign in ("campaign_b", "campaign_c"):
        for algorithm in ("hpac", "rac"):
            acc = defaultdict(list)
            for r in rows:
                if r["campaign_id"] == campaign and r["algorithm"] == algorithm:
                    acc[(int(r["n_nodes"]), r["coefficient_class"])].append(
                        float(r["median_elapsed_ns"]) / MS)
            fams = sorted({k[1] for k in acc})
            sizes = sorted({k[0] for k in acc})
            body = []
            for n in sizes:
                body.append([fmt(n).replace(".0", "")] +
                            [fmt(statistics.median(acc[(n, f)])) if (n, f) in acc else "--"
                             for f in fams])
            short = {"independent-positive": "ind-pos", "independent-signed": "ind-sgn",
                     "correlated": "corr", "anti-correlated": "anti",
                     "near-ties": "near", "exact-ties": "exact"}
            head = ["$n$"] + [f"\\texttt{{{short.get(f, f)}}}" for f in fams]
            write(out / f"rep_detail_{campaign}_{algorithm}.tex",
                  tabular(head, body, "r" + "r" * len(fams),
                          group=(f"median \\texttt{{{NICE[algorithm]}}} CPU time (ms) per family",
                                 2, len(fams) + 1)))

    # ---- plot data for every breakdown, so each table has a plot beside it ----
    FAM_ORDER = ["independent-positive", "independent-signed", "correlated",
                 "anti-correlated", "near-ties", "exact-ties"]

    def dat(path, header, rows_out):
        write(path, " ".join(header) + "\n" +
              "\n".join(" ".join(str(c) for c in r) for r in rows_out) + "\n")

    for campaign, algorithms in [
        ("campaign_b", ["pac", "hpac", "rac"]),
        ("campaign_c", ["hpac", "dhpac", "rac"]),
        ("campaign_e_in", ["hpac", "hipac", "rac"]),
        ("campaign_e_out", ["hpac", "hopac", "rac"]),
        ("campaign_d_path", ["pac", "hpac", "rac"]),
        ("campaign_d_binary", ["pac", "hpac", "rac"]),
        ("campaign_d_star", ["pac", "hpac", "rac"]),
    ]:
        # by density (random topologies only)
        acc = median_times(rows, campaign, algorithms, "rho")
        rhos = sorted({k[0] for k in acc if k[0]}, key=sort_key)
        if rhos:
            dat(out / f"rep_plotrho_{campaign}.dat", ["rho"] + algorithms,
                [[r] + [f"{statistics.median(acc[(r, a)]):.4f}" if (r, a) in acc else "nan"
                        for a in algorithms] for r in rhos])
        # by coefficient family (index 1..6, labels supplied in the axis)
        acc = median_times(rows, campaign, algorithms, "coefficient_class")
        fams = [f for f in FAM_ORDER if any((f, a) in acc for a in algorithms)]
        if fams:
            dat(out / f"rep_plotfam_{campaign}.dat", ["idx"] + algorithms,
                [[i + 1] + [f"{statistics.median(acc[(f, a)]):.4f}" if (f, a) in acc else "nan"
                            for a in algorithms] for i, f in enumerate(fams)])

    # paired ratios: by family and by density
    for campaign, num, den in [("campaign_b", "pac", "hpac"), ("campaign_b", "rac", "hpac"),
                               ("campaign_c", "rac", "hpac"),
                               ("campaign_d_path", "rac", "hpac"),
                               ("campaign_d_binary", "rac", "hpac"),
                               ("campaign_d_star", "rac", "hpac"),
                               ("campaign_d_star", "rac", "pac"),
                               ("campaign_e_in", "hipac", "hpac"),
                               ("campaign_e_out", "hopac", "hpac"),
                               ("campaign_e_in", "rac", "hpac"),
                               ("campaign_e_out", "rac", "hpac")]:
        acc = paired_ratio(rows, campaign, num, den, "coefficient_class")
        fams = [f for f in FAM_ORDER if f in acc]
        if fams:
            dat(out / f"rep_plotratiofam_{campaign}_{num}_{den}.dat", ["idx", "ratio"],
                [[i + 1, f"{statistics.median(acc[f]):.4f}"] for i, f in enumerate(fams)])
        acc = paired_ratio(rows, campaign, num, den, "rho")
        rhos = sorted({r for r in acc if r}, key=sort_key)
        if rhos:
            dat(out / f"rep_plotratiorho_{campaign}_{num}_{den}.dat", ["rho", "ratio"],
                [[r, f"{statistics.median(acc[r]):.4f}"] for r in rhos])

    # family x size detail, and timing dispersion, as plot data
    for campaign in ("campaign_b", "campaign_c"):
        for algorithm in ("hpac", "rac"):
            acc = defaultdict(list)
            for r in rows:
                if r["campaign_id"] == campaign and r["algorithm"] == algorithm:
                    acc[(int(r["n_nodes"]), r["coefficient_class"])].append(
                        float(r["median_elapsed_ns"]) / MS)
            sizes = sorted({k[0] for k in acc})
            cols = [f.replace("-", "") for f in FAM_ORDER]
            dat(out / f"rep_plotdetail_{campaign}_{algorithm}.dat", ["n"] + cols,
                [[n] + [f"{statistics.median(acc[(n, f)]):.4f}" if (n, f) in acc else "nan"
                        for f in FAM_ORDER] for n in sizes])

    for campaign, algorithms in [("campaign_c", ["hpac", "dhpac", "rac"]),
                                 ("campaign_e_in", ["hpac", "hipac", "rac"])]:
        acc = defaultdict(list)
        for r in rows:
            if r["campaign_id"] == campaign and r["algorithm"] in algorithms:
                med = float(r["median_elapsed_ns"])
                if med > 0:
                    acc[(int(r["n_nodes"]), r["algorithm"])].append(
                        100.0 * float(r["iqr_elapsed_ns"]) / med)
        sizes = sorted({k[0] for k in acc})
        dat(out / f"rep_plotiqr_{campaign}.dat", ["n"] + algorithms,
            [[n] + [f"{statistics.median(acc[(n, a)]):.3f}" if (n, a) in acc else "nan"
                    for a in algorithms] for n in sizes])

    # instance structure and layer counts as plot data
    struct = defaultdict(lambda: defaultdict(list))
    for r in rows:
        if r["campaign_id"] == "campaign_c" and r["algorithm"] == "hpac":
            struct[r["rho"]]["arcs"].append(int(r["n_arcs"]))
            struct[r["rho"]]["comp"].append(int(r["n_components"]))
            struct[r["rho"]]["layers"].append(int(r["n_layers"]))
    dat(out / "rep_plotstruct.dat", ["rho", "arcs", "comp", "layers"],
        [[r, f"{statistics.median(struct[r]['arcs']):.0f}",
          f"{statistics.median(struct[r]['comp']):.0f}",
          f"{statistics.median(struct[r]['layers']):.0f}"]
         for r in sorted(struct, key=sort_key)])

    lay = defaultdict(list)
    for r in rows:
        if r["campaign_id"] in ("campaign_b", "campaign_c") and r["algorithm"] == "hpac":
            lay[int(r["n_nodes"])].append(int(r["n_layers"]))
    dat(out / "rep_plotlayers.dat", ["n", "median", "min", "max"],
        [[n, f"{statistics.median(lay[n]):.0f}", min(lay[n]), max(lay[n])]
         for n in sorted(lay)])

    # ---- how many closure layers each family produces (explains the times) ----
    acc = defaultdict(list)
    for r in rows:
        if r["campaign_id"] in ("campaign_b", "campaign_c") and r["algorithm"] == "hpac":
            acc[(r["coefficient_class"], r["campaign_id"])].append(int(r["n_layers"]))
    families = sorted({k[0] for k in acc})
    body = []
    for family in families:
        cells = []
        for campaign in ("campaign_b", "campaign_c"):
            values = acc.get((family, campaign))
            cells.append(f"{statistics.median(values):.0f}" if values else "--")
        body.append([f"\\texttt{{{family}}}", *cells])
    write(out / "rep_layers_by_family.tex",
          tabular(["family", "$n\\le 1\\,000$", "$n\\ge 10\\,000$"], body, "lrr",
                  group=("median \\# closure layers", 2, 3)))


if __name__ == "__main__":
    main()
