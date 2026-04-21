from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def run(command):
    completed = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(completed.stdout)


def main():
    parser = argparse.ArgumentParser(description="Validate sequential and parallel runs on a small case.")
    parser.add_argument("--rows", type=int, default=32)
    parser.add_argument("--cols", type=int, default=32)
    parser.add_argument("--days", type=int, default=20)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "results" / "validation")
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    seq_grid = args.output_dir / "seq_grid.npy"
    par_grid = args.output_dir / "par_grid.npy"
    seq_csv = args.output_dir / "seq_stats.csv"
    par_csv = args.output_dir / "par_stats.csv"

    base = [
        "--rows",
        str(args.rows),
        "--cols",
        str(args.cols),
        "--days",
        str(args.days),
        "--seed",
        str(args.seed),
        "--capture-every",
        "9999",
    ]

    run(
        [
            sys.executable,
            str(ROOT / "sequential" / "run_sequential.py"),
            *base,
            "--stats-csv",
            str(seq_csv),
            "--final-grid",
            str(seq_grid),
        ]
    )
    run(
        [
            sys.executable,
            str(ROOT / "parallel" / "run_parallel.py"),
            *base,
            "--workers",
            str(args.workers),
            "--stats-csv",
            str(par_csv),
            "--final-grid",
            str(par_grid),
        ]
    )

    same_grid = np.array_equal(np.load(seq_grid), np.load(par_grid))
    same_stats = pd.read_csv(seq_csv).equals(pd.read_csv(par_csv))

    payload = {"same_grid": same_grid, "same_stats": same_stats}
    print(json.dumps(payload, indent=2))
    if not (same_grid and same_stats):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
