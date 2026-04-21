from __future__ import annotations

import argparse
from pathlib import Path

import imageio.v2 as imageio
from PIL import Image, ImageDraw


def load_frames(path: Path):
    return sorted(path.glob("frame_*.png"))


def label_frame(frame: Image.Image, title: str) -> Image.Image:
    canvas = Image.new("RGB", (frame.width, frame.height + 36), color=(255, 255, 255))
    canvas.paste(frame, (0, 36))
    draw = ImageDraw.Draw(canvas)
    draw.text((12, 10), title, fill=(20, 20, 20))
    return canvas


def main():
    parser = argparse.ArgumentParser(description="Build a side-by-side animation comparing runs.")
    parser.add_argument("--sequential-frames", type=Path, required=True)
    parser.add_argument("--parallel-frames", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fps", type=int, default=6)
    args = parser.parse_args()

    seq_paths = load_frames(args.sequential_frames)
    par_paths = load_frames(args.parallel_frames)
    frame_count = min(len(seq_paths), len(par_paths))
    if frame_count == 0:
        raise SystemExit("No frames found to animate.")

    frames = []
    for index in range(frame_count):
        seq = label_frame(Image.open(seq_paths[index]).convert("RGB"), "Secuencial")
        par = label_frame(Image.open(par_paths[index]).convert("RGB"), "Paralelo")
        combined = Image.new("RGB", (seq.width + par.width, max(seq.height, par.height)), color=(255, 255, 255))
        combined.paste(seq, (0, 0))
        combined.paste(par, (seq.width, 0))
        frames.append(combined)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    imageio.mimsave(args.output, [frame for frame in frames], duration=1.0 / args.fps)


if __name__ == "__main__":
    main()
