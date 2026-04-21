from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from common.sir_core import (  # noqa: E402
    DEAD,
    INFECTED,
    RECOVERED,
    SUSCEPTIBLE,
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


def run_simulation(config):
    current = create_initial_grid(config)
    stats_rows = []
    captured_frames = [render_frame(current)]
    cumulative_infected = int(np.count_nonzero(current == INFECTED))

    start = time.perf_counter()
    for day in range(1, config.days + 1):
        padded_rows = np.pad(current, ((1, 1), (0, 0)), constant_values=DEAD)
        next_grid, local_stats = update_block(padded_rows, day, 0, config)
        current = next_grid
        global_stats = aggregate_stats([local_stats], cumulative_infected)
        cumulative_infected = int(global_stats["cumulative_infected"])
        stats_rows.append(serialize_stats(day, global_stats))
        if day % max(config.capture_every, 1) == 0 or day == config.days:
            captured_frames.append(render_frame(current))
    elapsed = time.perf_counter() - start

    summary = {
        "mode": "sequential",
        "elapsed_seconds": elapsed,
        "final_counts": {
            "susceptible": int(np.count_nonzero(current == SUSCEPTIBLE)),
            "infected": int(np.count_nonzero(current == INFECTED)),
            "recovered": int(np.count_nonzero(current == RECOVERED)),
            "dead": int(np.count_nonzero(current == DEAD)),
        },
        "config": config.to_dict(),
        "days_recorded": len(stats_rows),
    }
    return current, stats_rows, captured_frames, summary


def main():
    parser = build_parser("Sequential 2-D grid SIR simulation.")
    args = parser.parse_args()
    config = parse_args_to_config(args)

    grid, stats_rows, frames, summary = run_simulation(config)

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
