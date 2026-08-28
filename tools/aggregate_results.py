#!/usr/bin/env python3
"""Aggregate raw pcf_benchmark CSV files into processed statistics.

Consumes one or more raw CSV files produced by pcf_benchmark / run_benchmark.py
(schema: campaign_id,instance,algorithm,repetition,order,elapsed_ns,...) and
produces, under --output-dir:

- processed.csv: one row per (campaign_id, instance, algorithm) with the
  median and interquartile range of elapsed_ns and peak_rss_kib across
  repetitions, instance metadata parsed from the filename convention used by
  tools/generate_random_instances.py and tools/generate_structured_instances.py,
  and a per-instance correctness_status (agreement of sequence_hash across
  every algorithm benchmarked together on that instance in that campaign).
- mismatches.csv: only the (campaign_id, instance) groups whose algorithms
  disagree on sequence_hash, for manual inspection.
- results_summary.json: citable totals (instance count, mismatch count,
  per-algorithm run count, per-campaign counts).

No algorithm is re-implemented here: this script only summarizes numbers
already computed by the C++ binaries.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
from collections import defaultdict
from pathlib import Path

RANDOM_RE = re.compile(r"^(?P<topology>gen|in|out)_n(?P<n>\d+)_rho(?P<rho>[0-9.]+)_(?P<family>[a-z-]+)_seed(?P<seed>\d+)$")
STRUCTURED_RE = re.compile(r"^(?P<shape>path|binary|star)_n(?P<n>\d+)_(?P<family>[a-z-]+)_seed(?P<seed>\d+)$")

TOPOLOGY_NAME = {"gen": "mixed-forest", "in": "in-forest", "out": "out-forest",
                 "path": "path-mixed", "binary": "binary-mixed", "star": "star-mixed"}


def parse_instance_metadata(instance_path: str) -> dict[str, str]:
    stem = Path(instance_path).stem
    match = RANDOM_RE.match(stem)
    if match:
        info = match.groupdict()
        return {"topology": TOPOLOGY_NAME[info["topology"]], "coefficient_class": info["family"],
                "rho": info["rho"], "seed": info["seed"]}
    match = STRUCTURED_RE.match(stem)
    if match:
        info = match.groupdict()
        return {"topology": TOPOLOGY_NAME[info["shape"]], "coefficient_class": info["family"],
                "rho": "", "seed": info["seed"]}
    return {"topology": "", "coefficient_class": "", "rho": "", "seed": ""}


def iqr(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    quantiles = statistics.quantiles(values, n=4, method="inclusive")
    return quantiles[2] - quantiles[0]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, nargs="+", required=True, help="raw CSV files or glob-expanded paths")
    parser.add_argument("--output-dir", type=Path, required=True)
    arguments = parser.parse_args()

    rows: list[dict[str, str]] = []
    for raw_path in arguments.raw:
        with raw_path.open(newline="", encoding="utf-8") as handle:
            rows.extend(csv.DictReader(handle))
    if not rows:
        raise SystemExit("no raw rows found")

    by_group: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_group[(row["campaign_id"], row["instance"], row["algorithm"])].append(row)

    by_instance: dict[tuple[str, str], set[str]] = defaultdict(set)
    for row in rows:
        by_instance[(row["campaign_id"], row["instance"])].add(row["sequence_hash"])

    processed: list[dict[str, object]] = []
    mismatches: list[dict[str, object]] = []
    for (campaign_id, instance, algorithm), group in sorted(by_group.items()):
        elapsed = [float(r["elapsed_ns"]) for r in group]
        rss = [float(r["peak_rss_kib"]) for r in group]
        meta = parse_instance_metadata(instance)
        hashes = by_instance[(campaign_id, instance)]
        status = "agreed" if len(hashes) == 1 else "mismatch"
        processed.append({
            "campaign_id": campaign_id,
            "instance": instance,
            "algorithm": algorithm,
            "repetitions": len(group),
            "median_elapsed_ns": statistics.median(elapsed),
            "iqr_elapsed_ns": iqr(elapsed),
            "median_peak_rss_kib": statistics.median(rss),
            "n_nodes": group[0]["n_nodes"],
            "n_arcs": group[0]["n_arcs"],
            "n_components": group[0]["n_components"],
            "n_layers": group[0]["n_layers"],
            "n_breakpoints": group[0]["n_breakpoints"],
            "correctness_status": status,
            "git_commit": group[0]["git_commit"],
            **meta,
        })
        if status == "mismatch":
            mismatches.append({
                "campaign_id": campaign_id, "instance": instance,
                "algorithms_in_group": sorted({r["algorithm"] for r in rows
                                                if (r["campaign_id"], r["instance"]) == (campaign_id, instance)}),
                "distinct_hashes": len(hashes),
            })

    arguments.output_dir.mkdir(parents=True, exist_ok=True)
    processed_path = arguments.output_dir / "processed.csv"
    with processed_path.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = list(processed[0].keys())
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(processed)

    mismatches_path = arguments.output_dir / "mismatches.csv"
    with mismatches_path.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = ["campaign_id", "instance", "algorithms_in_group", "distinct_hashes"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in mismatches:
            row = dict(row)
            row["algorithms_in_group"] = ";".join(row["algorithms_in_group"])
            writer.writerow(row)

    instances = {(r["campaign_id"], r["instance"]) for r in rows}
    algorithms = sorted({r["algorithm"] for r in rows})
    campaigns = sorted({r["campaign_id"] for r in rows})
    summary = {
        "n_raw_rows": len(rows),
        "n_instances": len(instances),
        "n_mismatched_instances": len(mismatches),
        "algorithms": algorithms,
        "campaigns": campaigns,
        "runs_per_algorithm": {alg: sum(1 for r in rows if r["algorithm"] == alg) for alg in algorithms},
    }
    (arguments.output_dir / "results_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"wrote {processed_path} ({len(processed)} rows), {mismatches_path} ({len(mismatches)} mismatches), "
          f"and results_summary.json")


if __name__ == "__main__":
    main()
