#!/usr/bin/env python3
"""Run the C++ benchmark reproducibly and write one raw CSV."""

from __future__ import annotations

import argparse
import csv
import subprocess
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--instances", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--algorithms", default="hfma,rac")
    parser.add_argument("--repetitions", type=int, default=11)
    parser.add_argument("--shuffle-seed", type=int)
    arguments = parser.parse_args()
    rows: list[dict[str, str]] = []
    for instance in sorted(arguments.instances.glob("*.pcf")):
        command = [str(arguments.binary), "--instance", str(instance), "--algorithms", arguments.algorithms,
                   "--repetitions", str(arguments.repetitions)]
        if arguments.shuffle_seed is not None:
            command += ["--shuffle-seed", str(arguments.shuffle_seed)]
        completed = subprocess.run(
            command,
            check=True, text=True, capture_output=True,
        )
        for row in csv.DictReader(completed.stdout.splitlines()):
            row["instance"] = instance.name
            rows.append(row)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    with arguments.output.open("w", newline="", encoding="utf-8") as output:
        fieldnames = tuple(rows[0].keys()) if rows else ("instance", "algorithm", "run", "order", "elapsed_ns", "macroitems")
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
