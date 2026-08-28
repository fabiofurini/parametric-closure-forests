#!/usr/bin/env python3
"""Build or verify deterministic SHA-256 manifests for .pcf instance sets."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import deque
from pathlib import Path


class DisjointSet:
    def __init__(self, size: int) -> None:
        self.parent = list(range(size))

    def find(self, node: int) -> int:
        while self.parent[node] != node:
            self.parent[node] = self.parent[self.parent[node]]
            node = self.parent[node]
        return node

    def join(self, left: int, right: int) -> bool:
        left, right = self.find(left), self.find(right)
        if left == right:
            return False
        self.parent[left] = right
        return True


def parse_instance(path: Path) -> tuple[int, list[int], list[int], list[tuple[int, int]]]:
    tokens = path.read_text(encoding="utf-8").split()
    cursor = 0

    def take(expected: str) -> None:
        nonlocal cursor
        if cursor >= len(tokens) or tokens[cursor] != expected:
            raise ValueError(f"{path}: expected {expected!r}")
        cursor += 1

    take("pcf")
    if cursor >= len(tokens) or tokens[cursor] != "1":
        raise ValueError(f"{path}: expected pcf format version 1")
    cursor += 1
    take("n")
    n = int(tokens[cursor])
    cursor += 1
    take("profits")
    profit = [int(value) for value in tokens[cursor:cursor + n]]
    cursor += n
    take("weights")
    weight = [int(value) for value in tokens[cursor:cursor + n]]
    cursor += n
    take("arcs")
    m = int(tokens[cursor])
    cursor += 1
    arcs = []
    for _ in range(m):
        tail, head = int(tokens[cursor]) - 1, int(tokens[cursor + 1]) - 1
        cursor += 2
        if not (0 <= tail < n and 0 <= head < n) or tail == head:
            raise ValueError(f"{path}: invalid arc")
        arcs.append((tail, head))
    if cursor != len(tokens) or n <= 0 or len(profit) != n or len(weight) != n or min(weight) <= 0:
        raise ValueError(f"{path}: malformed pcf payload")
    return n, profit, weight, arcs


def topology(n: int, arcs: list[tuple[int, int]]) -> tuple[str, int]:
    dsu = DisjointSet(n)
    indegree = [0] * n
    outdegree = [0] * n
    outgoing = [[] for _ in range(n)]
    for tail, head in arcs:
        if not dsu.join(tail, head):
            raise ValueError("underlying graph is not a forest")
        indegree[head] += 1
        outdegree[tail] += 1
        outgoing[tail].append(head)
    queue = deque(node for node in range(n) if indegree[node] == 0)
    visited = 0
    degrees = indegree[:]
    while queue:
        node = queue.popleft()
        visited += 1
        for successor in outgoing[node]:
            degrees[successor] -= 1
            if degrees[successor] == 0:
                queue.append(successor)
    if visited != n:
        raise ValueError("directed graph is not acyclic")
    is_in = max(outdegree, default=0) <= 1
    is_out = max(indegree, default=0) <= 1
    if is_in and is_out:
        label = "in-out-forest"
    elif is_in:
        label = "in-forest"
    elif is_out:
        label = "out-forest"
    else:
        label = "mixed-forest"
    return label, len({dsu.find(node) for node in range(n)})


def record(root: Path, path: Path) -> dict[str, object]:
    n, profit, weight, arcs = parse_instance(path)
    classification, components = topology(n, arcs)
    seed = re.search(r"(?:^|_)seed([0-9]+)(?:_|$)", path.stem)
    return {
        "instance_id": path.stem,
        "path": path.relative_to(root).as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "n_nodes": n,
        "n_arcs": len(arcs),
        "n_components": components,
        "topology": classification,
        "profit_min": min(profit),
        "profit_max": max(profit),
        "weight_min": min(weight),
        "weight_max": max(weight),
        "seed": int(seed.group(1)) if seed else None,
    }


def build(root: Path, generator_version: str) -> dict[str, object]:
    files = sorted(root.glob("*.pcf"))
    if not files:
        raise ValueError(f"no .pcf files directly in {root}")
    return {
        "format": "pcf-instance-manifest-v1",
        "generator_version": generator_version,
        "instances": [record(root, path) for path in files],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--instances", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--verify", type=Path)
    parser.add_argument("--generator-version", default="pcf-generators-v1")
    arguments = parser.parse_args()
    if (arguments.output is None) == (arguments.verify is None):
        raise SystemExit("select exactly one of --output or --verify")
    root = arguments.instances.resolve()
    if arguments.output:
        manifest = build(root, arguments.generator_version)
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    else:
        expected = json.loads(arguments.verify.read_text(encoding="utf-8"))
        actual = build(root, expected["generator_version"])
        if actual != expected:
            raise SystemExit("manifest verification failed")


if __name__ == "__main__":
    main()
