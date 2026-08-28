#!/usr/bin/env python3
"""Validate raw pcf_benchmark CSV files against the schema in section 11 of
docs/PIANO_PARTE_COMPUTAZIONALE.md before they are aggregated.

Checks, per row:
- every required column is present and non-empty;
- elapsed_ns, peak_rss_kib, n_nodes, n_arcs are positive integers;
- n_layers <= n_nodes and n_breakpoints == n_layers - 1;
- the referenced instance file exists on disk;
- RaC-only columns are populated exactly when algorithm == 'rac' and empty
  otherwise.

Exits non-zero and prints every violation found; does not modify any file.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

REQUIRED = ("campaign_id", "instance", "algorithm", "repetition", "order", "elapsed_ns",
            "n_layers", "n_breakpoints", "sequence_hash", "peak_rss_kib", "git_commit",
            "timestamp_utc", "n_nodes", "n_arcs", "n_components")
RAC_ONLY = ("rac_clusters", "rac_joins", "rac_internalizations", "rac_envelope_sum_calls",
            "rac_envelope_max_calls", "rac_hull_calls", "rac_lines_scanned", "rac_line_comparisons",
            "rac_rational_comparisons", "rac_pieces_stored", "rac_topdown_events", "rac_topdown_scans",
            "rac_expanded_vertices", "rac_expanded_edges", "rac_rounds", "rac_max_cluster_depth",
            "rac_estimated_bytes")


def validate_file(path: Path, instances_root: Path | None) -> list[str]:
    errors: list[str] = []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = [column for column in REQUIRED if column not in (reader.fieldnames or [])]
        if missing:
            return [f"{path}: missing required columns {missing}"]
        for line_number, row in enumerate(reader, start=2):
            where = f"{path}:{line_number}"
            for column in REQUIRED:
                if row.get(column, "") == "":
                    errors.append(f"{where}: empty required column {column!r}")
            try:
                elapsed = int(row["elapsed_ns"]); rss = int(row["peak_rss_kib"])
                n_nodes = int(row["n_nodes"]); n_arcs = int(row["n_arcs"])
                n_layers = int(row["n_layers"]); n_breakpoints = int(row["n_breakpoints"])
                if elapsed <= 0: errors.append(f"{where}: elapsed_ns must be positive")
                if rss <= 0: errors.append(f"{where}: peak_rss_kib must be positive")
                if n_nodes <= 0 or n_arcs < 0: errors.append(f"{where}: invalid n_nodes/n_arcs")
                if n_layers <= 0 or n_layers > n_nodes:
                    errors.append(f"{where}: n_layers out of range")
                if n_breakpoints != n_layers - 1:
                    errors.append(f"{where}: n_breakpoints must equal n_layers - 1")
            except (KeyError, ValueError):
                errors.append(f"{where}: non-integer numeric column")
            is_rac = row.get("algorithm") == "rac"
            for column in RAC_ONLY:
                value = row.get(column, "")
                if is_rac and value == "":
                    errors.append(f"{where}: RaC row missing {column!r}")
                if not is_rac and value != "":
                    errors.append(f"{where}: non-RaC row has non-empty {column!r}")
            if instances_root is not None:
                instance_path = Path(row["instance"])
                if not instance_path.is_absolute():
                    instance_path = instances_root / instance_path
                if not instance_path.exists():
                    errors.append(f"{where}: referenced instance not found: {instance_path}")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, nargs="+", required=True)
    parser.add_argument("--instances-root", type=Path, default=None,
                         help="base directory to resolve relative instance paths against")
    arguments = parser.parse_args()
    all_errors: list[str] = []
    for raw_path in arguments.raw:
        all_errors.extend(validate_file(raw_path, arguments.instances_root))
    if all_errors:
        for error in all_errors:
            print(error, file=sys.stderr)
        raise SystemExit(f"{len(all_errors)} schema violation(s) found")
    print(f"validated {len(arguments.raw)} raw file(s): no schema violations")


if __name__ == "__main__":
    main()
