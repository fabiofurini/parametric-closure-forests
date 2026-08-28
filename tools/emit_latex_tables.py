#!/usr/bin/env python3
"""Emit LaTeX table fragments from processed.csv (tools/aggregate_results.py output).

No numeric value in the emitted .tex is hand-typed: every cell is computed
here from the aggregated CSV, so the manuscript's computational tables can be
regenerated from raw data at any time (docs/PIANO_PARTE_COMPUTAZIONALE.md
section 12.4).

Two modes:

--mode correctness
    One row per campaign: instance count and mismatch count, read directly
    from results_summary.json in the same directory as processed.csv.

--mode ratio --baseline ALG_A --candidate ALG_B [--group-by n_nodes|topology]
    Median elapsed_ns ratio candidate/baseline, grouped by --group-by within
    one campaign, with the number of paired instances behind each ratio.
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path


def escape(text: str) -> str:
    return text.replace("_", r"\_")


def emit_correctness(output_dir: Path, out_path: Path) -> None:
    summary = json.loads((output_dir / "results_summary.json").read_text(encoding="utf-8"))
    with (output_dir / "mismatches.csv").open(newline="", encoding="utf-8") as handle:
        mismatches_by_campaign: dict[str, int] = defaultdict(int)
        for row in csv.DictReader(handle):
            mismatches_by_campaign[row["campaign_id"]] += 1
    lines = [
        r"\begin{tabular}{lrr}",
        r"\toprule",
        r"Campaign & Instances & Mismatches \\",
        r"\midrule",
    ]
    with (output_dir / "processed.csv").open(newline="", encoding="utf-8") as handle:
        instances_by_campaign: dict[str, set[str]] = defaultdict(set)
        for row in csv.DictReader(handle):
            instances_by_campaign[row["campaign_id"]].add(row["instance"])
    for campaign in summary["campaigns"]:
        lines.append(f"{escape(campaign)} & {len(instances_by_campaign[campaign])} & "
                      f"{mismatches_by_campaign.get(campaign, 0)} \\\\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {out_path}")


def emit_ratio(processed_csv: Path, campaign_id: str, baseline: str, candidate: str,
                group_by: str, out_path: Path) -> None:
    with processed_csv.open(newline="", encoding="utf-8") as handle:
        rows = [row for row in csv.DictReader(handle) if row["campaign_id"] == campaign_id]
    baseline_by_key: dict[tuple[str, str], float] = {}
    candidate_by_key: dict[tuple[str, str], float] = {}
    for row in rows:
        key = (row["instance"], row.get(group_by, ""))
        if row["algorithm"] == baseline:
            baseline_by_key[key] = float(row["median_elapsed_ns"])
        elif row["algorithm"] == candidate:
            candidate_by_key[key] = float(row["median_elapsed_ns"])
    ratios_by_group: dict[str, list[float]] = defaultdict(list)
    for (instance, group), base_value in baseline_by_key.items():
        cand_value = candidate_by_key.get((instance, group))
        if cand_value is not None and base_value > 0:
            ratios_by_group[group].append(cand_value / base_value)
    lines = [
        r"\begin{tabular}{lrrr}",
        r"\toprule",
        f"{escape(group_by)} & Paired instances & Median {escape(candidate)}/{escape(baseline)} & IQR \\\\",
        r"\midrule",
    ]

    def sort_key(value: str):
        try:
            return (0, float(value))
        except ValueError:
            return (1, value)

    for group in sorted(ratios_by_group, key=sort_key):
        values = sorted(ratios_by_group[group])
        median = statistics.median(values)
        spread = 0.0
        if len(values) >= 2:
            quantiles = statistics.quantiles(values, n=4, method="inclusive")
            spread = quantiles[2] - quantiles[0]
        lines.append(f"{escape(group)} & {len(values)} & {median:.3f} & {spread:.3f} \\\\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {out_path} ({len(ratios_by_group)} groups)")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("correctness", "ratio"), required=True)
    parser.add_argument("--processed-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--campaign-id")
    parser.add_argument("--baseline")
    parser.add_argument("--candidate")
    parser.add_argument("--group-by", default="n_nodes", choices=("n_nodes", "topology", "coefficient_class", "rho"))
    arguments = parser.parse_args()
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    if arguments.mode == "correctness":
        emit_correctness(arguments.processed_dir, arguments.output)
    else:
        if not (arguments.campaign_id and arguments.baseline and arguments.candidate):
            raise SystemExit("--mode ratio requires --campaign-id, --baseline and --candidate")
        emit_ratio(arguments.processed_dir / "processed.csv", arguments.campaign_id,
                   arguments.baseline, arguments.candidate, arguments.group_by, arguments.output)


if __name__ == "__main__":
    main()
