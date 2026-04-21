from __future__ import annotations

import concurrent.futures
import json
import sys
import time
from pathlib import Path
from typing import List, Tuple

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from common.sir_core import (   
    DEAD,
    INFECTED,
    RECOVERED,
    SUSCEPTIBLE,
    SimulationConfig,
    aggregate_stats,
    build_parser,
    create_initial_grid,
    parse_args_to_config,
    render_frame,
    save_frames,
    save_run_metadata,
    serialize_stats,
    update_block,
    write_stats_csv,
)


def row_chunks(rows: int, workers: int) -> List[Tuple[int, int]]:
    workers = max(1, min(workers, rows))
    base = rows // workers
    remainder = rows % workers
    chunks = []
    start = 0
    for worker in range(workers):
        extra = 1 if worker < remainder else 0
        end = start + base + extra
        chunks.append((start, end))
        start = end
    return chunks


def compute_local_block(task):
    prev, nxt, start_row, end_row, day, config = task
    ghost_start = max(0, start_row - 1)
    ghost_end = min(prev.shape[0], end_row + 1)
    block = prev[ghost_start:ghost_end, :]

    if start_row == 0:
        block = np.vstack([np.full((1, prev.shape[1]), DEAD, dtype=prev.dtype), block])
    if end_row == prev.shape[0]:
        block = np.vstack([block, np.full((1, prev.shape[1]), DEAD, dtype=prev.dtype)])

    next_block, stats = update_block(block, day, start_row, config)
    nxt[start_row:end_row, :] = next_block
    return stats


def run_parallel(config: SimulationConfig, workers: int):
    prev = create_initial_grid(config)
    nxt = np.empty_like(prev)

    chunks = row_chunks(config.rows, workers)
    stats_rows = []
    captured_frames = [render_frame(prev)]
    cumulative_infected = int(np.count_nonzero(prev == INFECTED))

    start = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        for day in range(1, config.days + 1):
            tasks = [
                (prev, nxt, start_row, end_row, day, config)
                for start_row, end_row in chunks
            ]
            partials = list(executor.map(compute_local_block, tasks))
            stats = aggregate_stats(partials, cumulative_infected)
            cumulative_infected = int(stats["cumulative_infected"])
            stats_rows.append(serialize_stats(day, stats))
            prev, nxt = nxt, prev
            if day % max(config.capture_every, 1) == 0 or day == config.days:
                captured_frames.append(render_frame(prev.copy()))
    elapsed = time.perf_counter() - start
    final_grid = prev.copy()

    summary = {
        "mode": "parallel",
        "workers": workers,
        "elapsed_seconds": elapsed,
        "final_counts": {
            "susceptible": int(np.count_nonzero(final_grid == SUSCEPTIBLE)),
            "infected": int(np.count_nonzero(final_grid == INFECTED)),
            "recovered": int(np.count_nonzero(final_grid == RECOVERED)),
            "dead": int(np.count_nonzero(final_grid == DEAD)),
        },
        "config": config.to_dict(),
        "days_recorded": len(stats_rows),
    }
    return final_grid, stats_rows, captured_frames, summary


def main():
    parser = build_parser("Parallel 2-D grid SIR simulation with row blocks and ghost cells.")
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    config = parse_args_to_config(args)

    grid, stats_rows, frames, summary = run_parallel(config, args.workers)

    if args.stats_csv:
        write_stats_csv(args.stats_csv, stats_rows)
    if args.final_grid:
        args.final_grid.parent.mkdir(parents=True, exist_ok=True)
        np.save(args.final_grid, grid)
    save_frames(args.frames_dir, frames)
    save_run_metadata(args.metadata_json, summary)

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
