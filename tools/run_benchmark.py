#!/usr/bin/env python3
"""Run the C++ benchmark reproducibly and write one raw CSV.

Every instance is run in its own subprocess with a wall-clock timeout and,
optionally, a virtual-memory ceiling (docs/EXPERIMENTAL_PROTOCOL.md, "Known
measurement limitation" / OOM censoring): a run that exceeds either is
recorded as a censored event in --failures-log and the campaign continues
with the next instance, instead of aborting the whole batch. This matters in
practice: HPaC on large mixed-star instances can exhaust tens of gigabytes
of RAM before throwing std::bad_alloc (see docs/PIANO_PARTE_COMPUTAZIONALE.md
section 12.3.6/12.3.11), and a single such instance must not lose every
other result already collected in the same campaign.
"""
from __future__ import annotations

import argparse
import csv
import subprocess
from pathlib import Path


def run_one(binary: Path, instance: Path, algorithms: str, repetitions: int, campaign_id: str,
            shuffle_seed: int | None, timeout_seconds: float, memory_limit_kib: int | None) -> tuple[list[dict[str, str]], str | None]:
    command = [str(binary), "--instance", str(instance), "--algorithms", algorithms,
               "--repetitions", str(repetitions), "--campaign-id", campaign_id]
    if shuffle_seed is not None:
        command += ["--shuffle-seed", str(shuffle_seed)]
    if memory_limit_kib is not None:
        # Cap RLIMIT_AS in the child shell before exec'ing the benchmark, so a
        # memory blow-up fails as a clean allocation error instead of risking
        # the host's own memory.
        quoted = " ".join(f"'{part}'" for part in command)
        command = ["bash", "-c", f"ulimit -v {memory_limit_kib}; exec {quoted}"]
    try:
        completed = subprocess.run(command, check=True, text=True, capture_output=True, timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        return [], "timeout"
    except subprocess.CalledProcessError as error:
        stderr_tail = (error.stderr or "").strip().splitlines()[-1:] or [""]
        reason = "oom" if "bad_alloc" in (error.stderr or "") else f"exit_{error.returncode}:{stderr_tail[0]}"
        return [], reason
    rows = list(csv.DictReader(completed.stdout.splitlines()))
    for row in rows:
        row["instance"] = instance.name
    return rows, None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--instances", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--algorithms", default="hpac,rac")
    parser.add_argument("--repetitions", type=int, default=11)
    parser.add_argument("--shuffle-seed", type=int)
    parser.add_argument("--campaign-id", default="unspecified")
    parser.add_argument("--timeout-seconds", type=float, default=300.0)
    parser.add_argument("--memory-limit-kib", type=int, default=None,
                         help="virtual-memory ceiling per instance run, via `ulimit -v`")
    parser.add_argument("--failures-log", type=Path, default=None,
                         help="defaults to <output>.failures.csv")
    arguments = parser.parse_args()
    failures_log = arguments.failures_log or arguments.output.with_suffix(".failures.csv")

    rows: list[dict[str, str]] = []
    failures: list[dict[str, str]] = []
    instances = sorted(arguments.instances.glob("*.pcf"))
    for index, instance in enumerate(instances, start=1):
        instance_rows, failure_reason = run_one(
            arguments.binary, instance, arguments.algorithms, arguments.repetitions,
            arguments.campaign_id, arguments.shuffle_seed, arguments.timeout_seconds, arguments.memory_limit_kib,
        )
        if failure_reason is not None:
            failures.append({"instance": instance.name, "reason": failure_reason})
            print(f"[{index}/{len(instances)}] {instance.name}: {failure_reason}")
        else:
            rows.extend(instance_rows)
            print(f"[{index}/{len(instances)}] {instance.name}: ok ({len(instance_rows)} rows)")

    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    with arguments.output.open("w", newline="", encoding="utf-8") as output:
        fieldnames = tuple(rows[0].keys()) if rows else (
            "campaign_id", "instance", "algorithm", "repetition", "order", "elapsed_ns")
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    with failures_log.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=("instance", "reason"))
        writer.writeheader()
        writer.writerows(failures)

    print(f"wrote {arguments.output} ({len(rows)} rows), {failures_log} ({len(failures)} censored instances)")


if __name__ == "__main__":
    main()
