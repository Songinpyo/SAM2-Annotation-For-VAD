"""
Generate `data/shanghaitech/annotations.txt` from frame-level mask `.npy` files.

This project uses two different "annotation" concepts:
1) Dataset-level temporal intervals (this script generates those for ShanghaiTech).
2) Tool-level per-frame bbox/point annotations (saved under `annotations/<run_name>/...`).

ShanghaiTechAdapter expects whitespace-separated lines with 5 fields:
    video_name total_frames anomaly_flag start_frame end_frame

We derive these from `data/shanghaitech/test_frame_mask/*.npy`, where each `.npy` is a
1D array (length = total_frames) with 0/1 indicating normal/anomaly per frame.

If a mask has no anomaly frames, we write:
    anomaly_flag = 0, start_frame = 0, end_frame = total_frames - 1
Otherwise we write a single merged interval:
    anomaly_flag = 1, start_frame = first anomalous frame index, end_frame = last anomalous frame index

Run (recommended with your conda env "gpt"):
    conda run -n gpt python generate_shanghaitech_annotations_from_masks.py
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class ShanghaiTechTemporalAnnotation:
    """A single temporal annotation line for ShanghaiTechAdapter."""

    video_name: str
    total_frames: int
    anomaly_flag: int
    start_frame: int
    end_frame: int

    def to_line(self) -> str:
        return (
            f"{self.video_name} {self.total_frames} {self.anomaly_flag} "
            f"{self.start_frame} {self.end_frame}"
        )


def _load_frame_mask(mask_path: Path) -> np.ndarray:
    """
    Load a frame-level anomaly mask.

    The expected canonical shape is (T,), dtype can vary (uint8/bool/int).
    """
    arr = np.load(mask_path, allow_pickle=False)
    if arr.ndim == 0:
        arr = np.array([arr])
    return arr


def _mask_to_interval(mask: np.ndarray) -> tuple[int, int, int]:
    """
    Convert a frame-level mask to (anomaly_flag, start_frame, end_frame).

    Notes:
    - Uses 0-based frame indices.
    - If multiple disjoint anomaly segments exist, returns the union [min, max]
      because ShanghaiTechAdapter currently supports a single interval per video.
    """
    if mask.size == 0:
        raise ValueError("Mask has zero length; cannot infer total_frames.")

    is_anom = mask.astype(np.int64) > 0
    if not np.any(is_anom):
        return 0, 0, int(mask.size - 1)

    idx = np.flatnonzero(is_anom)
    return 1, int(idx[0]), int(idx[-1])


def generate_annotations(masks_dir: Path) -> list[ShanghaiTechTemporalAnnotation]:
    """Generate temporal annotations from all `.npy` masks in a directory."""
    if not masks_dir.exists() or not masks_dir.is_dir():
        raise FileNotFoundError(f"Masks directory not found: {masks_dir}")

    mask_paths = sorted(masks_dir.glob("*.npy"))
    if not mask_paths:
        raise FileNotFoundError(f"No .npy files found under: {masks_dir}")

    annotations: list[ShanghaiTechTemporalAnnotation] = []
    for mask_path in mask_paths:
        video_name = mask_path.stem  # e.g., "01_0014"
        mask = _load_frame_mask(mask_path)
        total_frames = int(mask.size)
        anomaly_flag, start_frame, end_frame = _mask_to_interval(mask)

        annotations.append(
            ShanghaiTechTemporalAnnotation(
                video_name=video_name,
                total_frames=total_frames,
                anomaly_flag=anomaly_flag,
                start_frame=start_frame,
                end_frame=end_frame,
            )
        )

    # Keep deterministic ordering
    annotations.sort(key=lambda a: a.video_name)
    return annotations


def write_annotations(annotations: list[ShanghaiTechTemporalAnnotation], output_path: Path) -> None:
    """Write annotations in ShanghaiTechAdapter whitespace format."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [a.to_line() for a in annotations]
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Generate ShanghaiTech annotations.txt from frame mask .npy files.")
    p.add_argument(
        "--masks-dir",
        type=Path,
        default=Path("data/shanghaitech/test_frame_mask"),
        help="Directory containing frame-level mask .npy files.",
    )
    p.add_argument(
        "--output",
        type=Path,
        default=Path("data/shanghaitech/annotations.txt"),
        help="Output annotations.txt path.",
    )
    return p


def main() -> None:
    args = _build_argparser().parse_args()

    annotations = generate_annotations(args.masks_dir)
    write_annotations(annotations, args.output)

    num_anom = sum(a.anomaly_flag == 1 for a in annotations)
    num_normal = len(annotations) - num_anom
    print(f"Wrote {len(annotations)} lines to: {args.output}")
    print(f"- anomaly videos: {num_anom}")
    print(f"- normal videos:  {num_normal}")


if __name__ == "__main__":
    main()

