#!/usr/bin/env python3
"""Generate deterministic closure-format path, binary and mixed-star instances.

Coefficients follow the six closure-specific affine families defined in
tools/pcf_families.py. Each underlying edge is oriented independently with
probability 1/2, as required by docs/PIANO_PARTE_COMPUTAZIONALE.md section 8.2.
"""

from __future__ import annotations

import argparse
import random
from pathlib import Path

from pcf_families import FAMILIES, make_coefficients


def arcs(n: int, shape: str, rng: random.Random) -> list[tuple[int, int]]:
    result: list[tuple[int, int]] = []
    for v in range(1, n):
        parent = 0 if shape == "star" else ((v - 1) // 2 if shape == "binary" else v - 1)
        result.append((parent, v) if rng.random() < 0.5 else (v, parent))
    return result


def write_instance(path: Path, n: int, shape: str, family: str, seed: int) -> None:
    rng = random.Random(seed)
    profits, weights = make_coefficients(n, family, rng)
    edge_list = arcs(n, shape, rng)
    with path.open("w", encoding="utf-8") as output:
        output.write("pcf 1\n")
        output.write(f"n {n}\n")
        output.write("profits " + " ".join(map(str, profits)) + "\n")
        output.write("weights " + " ".join(map(str, weights)) + "\n")
        output.write(f"arcs {len(edge_list)}\n")
        for u, v in edge_list:
            output.write(f"{u + 1} {v + 1}\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--shape", choices=("path", "binary", "star"), required=True)
    parser.add_argument("--sizes", default="100,200,500,1000,2000")
    parser.add_argument("--families", default=",".join(FAMILIES))
    parser.add_argument("--seeds", type=int, default=10)
    arguments = parser.parse_args()
    arguments.output.mkdir(parents=True, exist_ok=True)
    for n in (int(value) for value in arguments.sizes.split(",")):
        for family in arguments.families.split(","):
            for seed in range(arguments.seeds):
                write_instance(
                    arguments.output / f"{arguments.shape}_n{n}_{family}_seed{seed}.pcf",
                    n, arguments.shape, family, seed + 100000 * n,
                )


if __name__ == "__main__":
    main()
