#!/usr/bin/env python3
"""Generate random-topology closure instances in the independent pcf format.

Coefficients follow the six closure-specific affine families defined in
tools/pcf_families.py (see docs/PIANO_PARTE_COMPUTAZIONALE.md section 8.3).
Topologies follow section 8.1: 'gen' orients each underlying-forest edge
independently (mixed-forest/mixed-tree), 'in' caps out-degree at one
(in-forest), 'out' caps in-degree at one (out-forest).
"""
from __future__ import annotations
import argparse
import random
from pathlib import Path

from pcf_families import FAMILIES, make_coefficients


def make_arcs(n: int, density: float, topology: str, rng: random.Random) -> list[tuple[int, int]]:
    edges = []
    if topology == 'in':
        for u in range(n - 1):
            if rng.random() < density: edges.append((u, rng.randrange(u + 1, n)))
        return edges
    if topology == 'out':
        for v in range(1, n):
            if rng.random() < density: edges.append((rng.randrange(v), v))
        return edges
    for v in range(1, n):
        if rng.random() < density:
            u = rng.randrange(v)
            edges.append((u, v) if rng.random() < 0.5 else (v, u))
    return edges


def write(path: Path, n: int, density: float, topology: str, family: str, seed: int) -> None:
    rng = random.Random(seed)
    profits, weights = make_coefficients(n, family, rng)
    edges = make_arcs(n, density, topology, rng)
    with path.open('w', encoding='utf-8') as out:
        out.write(f'pcf 1\nn {n}\nprofits ' + ' '.join(map(str, profits)) + '\n')
        out.write('weights ' + ' '.join(map(str, weights)) + f'\narcs {len(edges)}\n')
        for u, v in edges: out.write(f'{u + 1} {v + 1}\n')


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--sizes', default='100,200,500,1000')
    parser.add_argument('--densities', default='0.3,0.6,0.9,1.0')
    parser.add_argument('--topology', choices=('gen', 'in', 'out'), default='gen')
    parser.add_argument('--families', default=','.join(FAMILIES))
    parser.add_argument('--seeds', type=int, default=3)
    args = parser.parse_args(); args.output.mkdir(parents=True, exist_ok=True)
    for n in map(int, args.sizes.split(',')):
        for density in map(float, args.densities.split(',')):
            for family in args.families.split(','):
                for seed in range(args.seeds):
                    write(args.output / f'{args.topology}_n{n}_rho{density}_{family}_seed{seed}.pcf',
                          n, density, args.topology, family, seed + 100000 * n + int(100 * density))


if __name__ == '__main__': main()
