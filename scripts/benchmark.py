from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_command(command):
    completed = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(completed.stdout)


def main():
    parser = argparse.ArgumentParser(description="Run strong-scaling experiments.")
    parser.add_argument("--rows", type=int, default=1000)
    parser.add_argument("--cols", type=int, default=1000)
    parser.add_argument("--days", type=int, default=365)
    parser.add_argument("--beta", type=float, default=0.24)
    parser.add_argument("--gamma", type=float, default=0.07)
    parser.add_argument("--mu", type=float, default=0.01)
    parser.add_argument("--initial-infected", type=int, default=25)
    parser.add_argument("--seed", type=int, default=12345)
    parser.add_argument("--capture-every", type=int, default=30)
    parser.add_argument("--workers", nargs="+", type=int, default=[1, 2, 4, 8])
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "results" / "benchmark" / "strong_scaling.csv",
    )
    args = parser.parse_args()

    base_args = [
        "--rows",
        str(args.rows),
        "--cols",
        str(args.cols),
        "--days",
        str(args.days),
        "--beta",
        str(args.beta),
        "--gamma",
        str(args.gamma),
        "--mu",
        str(args.mu),
        "--initial-infected",
        str(args.initial_infected),
        "--seed",
        str(args.seed),
        "--capture-every",
        str(args.capture_every),
    ]

    sequential_cmd = [
        sys.executable,
        str(ROOT / "sequential" / "run_sequential.py"),
        *base_args,
    ]
    sequential = run_command(sequential_cmd)
    seq_time = sequential["elapsed_seconds"]

    rows = [
        {
            "mode": "sequential",
            "workers": 1,
            "elapsed_seconds": seq_time,
            "speedup_vs_seq": 1.0,
        }
    ]

    for workers in args.workers:
        parallel_cmd = [
            sys.executable,
            str(ROOT / "parallel" / "run_parallel.py"),
            *base_args,
            "--workers",
            str(workers),
        ]
        summary = run_command(parallel_cmd)
        rows.append(
            {
                "mode": "parallel",
                "workers": workers,
                "elapsed_seconds": summary["elapsed_seconds"],
                "speedup_vs_seq": seq_time / summary["elapsed_seconds"],
            }
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["mode", "workers", "elapsed_seconds", "speedup_vs_seq"],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(json.dumps({"output": str(args.output), "rows": rows}, indent=2))


if __name__ == "__main__":
    main()
