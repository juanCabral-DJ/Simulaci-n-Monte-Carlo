from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np


SUSCEPTIBLE = np.uint8(0)
INFECTED = np.uint8(1)
RECOVERED = np.uint8(2)
DEAD = np.uint8(3)

STATE_COLORS = np.array(
    [
        [240, 240, 240],
        [214, 39, 40],
        [44, 160, 44],
        [31, 31, 31],
    ],
    dtype=np.uint8,
)


@dataclass(frozen=True)
class SimulationConfig:
    rows: int = 1000
    cols: int = 1000
    days: int = 365
    beta: float = 0.24
    gamma: float = 0.07
    mu: float = 0.01
    initial_infected: int = 25
    seed: int = 12345
    capture_every: int = 10

    def to_dict(self) -> Dict[str, float | int]:
        return asdict(self)


def _splitmix64(x: np.ndarray) -> np.ndarray:
    x = (x + np.uint64(0x9E3779B97F4A7C15)) & np.uint64(0xFFFFFFFFFFFFFFFF)
    z = x
    z = ((z ^ (z >> np.uint64(30))) * np.uint64(0xBF58476D1CE4E5B9)) & np.uint64(
        0xFFFFFFFFFFFFFFFF
    )
    z = ((z ^ (z >> np.uint64(27))) * np.uint64(0x94D049BB133111EB)) & np.uint64(
        0xFFFFFFFFFFFFFFFF
    )
    return z ^ (z >> np.uint64(31))


def deterministic_random(
    day: int,
    rows: np.ndarray,
    cols: np.ndarray,
    stream: int,
    seed: int,
) -> np.ndarray:
    with np.errstate(over="ignore"):
        day_term = np.uint64(day + 1) * np.uint64(0xD1B54A32D192ED03)
        row_term = rows.astype(np.uint64) * np.uint64(0x9E3779B97F4A7C15)
        col_term = cols.astype(np.uint64) * np.uint64(0x94D049BB133111EB)
        stream_term = np.uint64(stream + 1) * np.uint64(0xBF58476D1CE4E5B9)
        seed_term = np.uint64(seed) * np.uint64(0xDB4F0B9175AE2165)
    mixed = _splitmix64(day_term ^ row_term ^ col_term ^ stream_term ^ seed_term)
    return mixed.astype(np.float64) / np.float64(2**64 - 1)


def create_initial_grid(config: SimulationConfig) -> np.ndarray:
    grid = np.full((config.rows, config.cols), SUSCEPTIBLE, dtype=np.uint8)
    rng = np.random.default_rng(config.seed)
    chosen = rng.choice(config.rows * config.cols, size=config.initial_infected, replace=False)
    grid.flat[chosen] = INFECTED
    return grid


def compute_neighbor_counts(padded_infected: np.ndarray) -> np.ndarray:
    return (
        padded_infected[:-2, :-2]
        + padded_infected[:-2, 1:-1]
        + padded_infected[:-2, 2:]
        + padded_infected[1:-1, :-2]
        + padded_infected[1:-1, 2:]
        + padded_infected[2:, :-2]
        + padded_infected[2:, 1:-1]
        + padded_infected[2:, 2:]
    )


def update_block(
    prev_with_ghost_rows: np.ndarray,
    day: int,
    row_offset: int,
    config: SimulationConfig,
) -> Tuple[np.ndarray, Dict[str, float]]:
    padded = np.pad(prev_with_ghost_rows, ((0, 0), (1, 1)), constant_values=DEAD)
    infected = (padded == INFECTED).astype(np.uint8)
    infected_neighbors = compute_neighbor_counts(infected)

    center = prev_with_ghost_rows[1:-1, :]
    next_center = center.copy()

    row_ids = np.arange(row_offset, row_offset + center.shape[0], dtype=np.uint64)[:, None]
    col_ids = np.arange(center.shape[1], dtype=np.uint64)[None, :]

    infection_prob = 1.0 - np.power(1.0 - config.beta, infected_neighbors, dtype=np.float64)
    infection_draw = deterministic_random(day, row_ids, col_ids, 0, config.seed)
    infection_mask = (center == SUSCEPTIBLE) & (infected_neighbors > 0) & (
        infection_draw < infection_prob
    )
    next_center[infection_mask] = INFECTED

    infected_mask = center == INFECTED
    recovery_draw = deterministic_random(day, row_ids, col_ids, 1, config.seed)
    death_draw = deterministic_random(day, row_ids, col_ids, 2, config.seed)

    death_mask = infected_mask & (death_draw < config.mu)
    recovery_mask = infected_mask & ~death_mask & (recovery_draw < config.gamma)
    stay_infected_mask = infected_mask & ~death_mask & ~recovery_mask

    next_center[death_mask] = DEAD
    next_center[recovery_mask] = RECOVERED
    next_center[stay_infected_mask] = INFECTED

    currently_infected = int(infected_mask.sum())
    new_infections = int(infection_mask.sum())
    day_r = float(new_infections / currently_infected) if currently_infected else 0.0

    stats = {
        "susceptible": int(np.count_nonzero(next_center == SUSCEPTIBLE)),
        "infected": int(np.count_nonzero(next_center == INFECTED)),
        "recovered": int(np.count_nonzero(next_center == RECOVERED)),
        "dead": int(np.count_nonzero(next_center == DEAD)),
        "new_infections": new_infections,
        "currently_infected": currently_infected,
        "day_r": day_r,
    }
    return next_center, stats


def aggregate_stats(parts: Iterable[Dict[str, float]], cumulative_infected: int) -> Dict[str, float]:
    total = {
        "susceptible": 0,
        "infected": 0,
        "recovered": 0,
        "dead": 0,
        "new_infections": 0,
        "currently_infected": 0,
        "weighted_r_numerator": 0.0,
        "weighted_r_denominator": 0,
    }

    for part in parts:
        total["susceptible"] += int(part["susceptible"])
        total["infected"] += int(part["infected"])
        total["recovered"] += int(part["recovered"])
        total["dead"] += int(part["dead"])
        total["new_infections"] += int(part["new_infections"])
        total["currently_infected"] += int(part["currently_infected"])
        total["weighted_r_numerator"] += float(part["day_r"]) * int(part["currently_infected"])
        total["weighted_r_denominator"] += int(part["currently_infected"])

    total["cumulative_infected"] = cumulative_infected + total["new_infections"]
    if total["weighted_r_denominator"]:
        total["R_t"] = total["weighted_r_numerator"] / total["weighted_r_denominator"]
    else:
        total["R_t"] = 0.0
    total["R0_proxy"] = total["R_t"]
    return total


def stats_header() -> List[str]:
    return [
        "day",
        "susceptible",
        "infected",
        "recovered",
        "dead",
        "new_infections",
        "cumulative_infected",
        "currently_infected",
        "R_t",
        "R0_proxy",
    ]


def serialize_stats(day: int, stats: Dict[str, float]) -> Dict[str, float]:
    return {
        "day": day,
        "susceptible": int(stats["susceptible"]),
        "infected": int(stats["infected"]),
        "recovered": int(stats["recovered"]),
        "dead": int(stats["dead"]),
        "new_infections": int(stats["new_infections"]),
        "cumulative_infected": int(stats["cumulative_infected"]),
        "currently_infected": int(stats["currently_infected"]),
        "R_t": float(stats["R_t"]),
        "R0_proxy": float(stats["R0_proxy"]),
    }


def write_stats_csv(path: Path, rows: List[Dict[str, float]]) -> None:
    import csv

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=stats_header())
        writer.writeheader()
        writer.writerows(rows)


def render_frame(grid: np.ndarray) -> np.ndarray:
    return STATE_COLORS[grid]


def save_animation_gif(frames: List[np.ndarray], path: Path, fps: int = 10) -> None:
    import imageio.v2 as imageio

    path.parent.mkdir(parents=True, exist_ok=True)
    imageio.mimsave(path, frames, duration=1.0 / fps)


def parse_args_to_config(args) -> SimulationConfig:
    return SimulationConfig(
        rows=args.rows,
        cols=args.cols,
        days=args.days,
        beta=args.beta,
        gamma=args.gamma,
        mu=args.mu,
        initial_infected=args.initial_infected,
        seed=args.seed,
        capture_every=args.capture_every,
    )


def build_parser(description: str):
    import argparse

    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--rows", type=int, default=1000)
    parser.add_argument("--cols", type=int, default=1000)
    parser.add_argument("--days", type=int, default=365)
    parser.add_argument("--beta", type=float, default=0.24)
    parser.add_argument("--gamma", type=float, default=0.07)
    parser.add_argument("--mu", type=float, default=0.01)
    parser.add_argument("--initial-infected", type=int, default=25)
    parser.add_argument("--seed", type=int, default=12345)
    parser.add_argument("--capture-every", type=int, default=10)
    parser.add_argument("--frames-dir", type=Path, default=None)
    parser.add_argument("--stats-csv", type=Path, default=None)
    parser.add_argument("--final-grid", type=Path, default=None)
    parser.add_argument("--metadata-json", type=Path, default=None)
    return parser


def save_run_metadata(path: Optional[Path], payload: Dict[str, object]) -> None:
    if path is None:
        return
    import json

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def save_frames(frames_dir: Optional[Path], frames: List[np.ndarray]) -> None:
    if frames_dir is None:
        return

    from PIL import Image

    frames_dir.mkdir(parents=True, exist_ok=True)
    for index, frame in enumerate(frames):
        Image.fromarray(frame).save(frames_dir / f"frame_{index:04d}.png")
