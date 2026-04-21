from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def main():
    parser = argparse.ArgumentParser(description="Plot strong-scaling speed-up.")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    df = pd.read_csv(args.input)
    parallel = df[df["mode"] == "parallel"].sort_values("workers")

    plt.style.use("seaborn-v0_8-whitegrid")
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(parallel["workers"], parallel["speedup_vs_seq"], marker="o", linewidth=2.5)
    ax.plot(parallel["workers"], parallel["workers"], linestyle="--", color="gray", label="Ideal")
    ax.set_title("Strong Scaling del Modelo SIR Paralelo")
    ax.set_xlabel("Núcleos")
    ax.set_ylabel("Speed-up vs. secuencial")
    ax.legend()
    fig.tight_layout()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, dpi=180)


if __name__ == "__main__":
    main()
