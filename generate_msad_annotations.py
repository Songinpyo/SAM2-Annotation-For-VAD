"""
Generate MSAD temporal annotation text files for this tool.

Input files:
- data/msad/anomaly_annotation.csv
- data/msad/MSAD_I3D_WS_Train.list
- data/msad/MSAD_I3D_WS_Test.list

Output files:
- data/msad/annotations_train.txt
- data/msad/annotations_test.txt

Output format per line:
    video_name total_frames anomaly_flag start_frame end_frame

Notes:
- `video_name` uses the relative path style expected by this project:
    "{class_name}/{clip_name}"  (without extension)
- CSV anomaly frame indices are treated as 1-based and converted to 0-based.
- Entries present in list files but absent in CSV are skipped (normal videos).
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MSADTemporalAnnotation:
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


def _build_argparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate MSAD train/test annotation txt files.")
    parser.add_argument(
        "--csv",
        type=Path,
        default=Path("data/msad/anomaly_annotation.csv"),
        help="MSAD anomaly CSV path.",
    )
    parser.add_argument(
        "--train-list",
        type=Path,
        default=Path("data/msad/MSAD_I3D_WS_Train.list"),
        help="Train split list path.",
    )
    parser.add_argument(
        "--test-list",
        type=Path,
        default=Path("data/msad/MSAD_I3D_WS_Test.list"),
        help="Test split list path.",
    )
    parser.add_argument(
        "--train-output",
        type=Path,
        default=Path("data/msad/annotations_train.txt"),
        help="Output train annotation txt path.",
    )
    parser.add_argument(
        "--test-output",
        type=Path,
        default=Path("data/msad/annotations_test.txt"),
        help="Output test annotation txt path.",
    )
    return parser


def _parse_list_names(list_path: Path) -> list[str]:
    if not list_path.exists():
        raise FileNotFoundError(f"List file not found: {list_path}")

    names: list[str] = []
    with list_path.open("r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue

            filename = Path(line).name
            if filename.endswith("_i3d.npy"):
                clip_name = filename[: -len("_i3d.npy")]
            else:
                clip_name = Path(filename).stem

            names.append(clip_name)

    return names


def _to_zero_based(total_frames: int, start_1b: int, end_1b: int) -> tuple[int, int]:
    if total_frames <= 0:
        raise ValueError(f"Invalid total_frames={total_frames}.")

    max_idx = total_frames - 1
    start_0b = max(0, start_1b - 1)
    end_0b = max(0, end_1b - 1)

    start_0b = min(start_0b, max_idx)
    end_0b = min(end_0b, max_idx)

    if end_0b < start_0b:
        raise ValueError(
            "Invalid interval after 0-based conversion: "
            f"total={total_frames}, start_1b={start_1b}, end_1b={end_1b}"
        )

    return start_0b, end_0b


def _load_csv_annotations(csv_path: Path) -> dict[str, MSADTemporalAnnotation]:
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    mapping: dict[str, MSADTemporalAnnotation] = {}
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)

        required_cols = {
            "name",
            "total frames",
            "starting frame of anomaly",
            "ending frame of anomaly",
        }
        missing_cols = required_cols - set(reader.fieldnames or [])
        if missing_cols:
            raise ValueError(f"Missing required columns in CSV: {sorted(missing_cols)}")

        for row in reader:
            name = str(row["name"]).strip()
            if not name:
                continue

            total_frames = int(row["total frames"])
            start_1b = int(row["starting frame of anomaly"])
            end_1b = int(row["ending frame of anomaly"])
            start_0b, end_0b = _to_zero_based(total_frames, start_1b, end_1b)

            # Example: "Traffic_accident_12" -> class "Traffic_accident"
            class_name = name.rsplit("_", 1)[0]
            video_name = f"{class_name}/{name}"

            mapping[name] = MSADTemporalAnnotation(
                video_name=video_name,
                total_frames=total_frames,
                anomaly_flag=1,
                start_frame=start_0b,
                end_frame=end_0b,
            )

    return mapping


def _build_split_annotations(
    split_names: list[str], csv_map: dict[str, MSADTemporalAnnotation]
) -> tuple[list[MSADTemporalAnnotation], list[str]]:
    annotations: list[MSADTemporalAnnotation] = []
    skipped_names: list[str] = []
    seen: set[str] = set()

    for clip_name in split_names:
        if clip_name in seen:
            continue
        seen.add(clip_name)

        ann = csv_map.get(clip_name)
        if ann is None:
            skipped_names.append(clip_name)
            continue

        annotations.append(ann)

    return annotations, skipped_names


def _write_annotations(output_path: Path, annotations: list[MSADTemporalAnnotation]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [ann.to_line() for ann in annotations]
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = _build_argparser().parse_args()

    csv_map = _load_csv_annotations(args.csv)

    train_names = _parse_list_names(args.train_list)
    test_names = _parse_list_names(args.test_list)

    train_annotations, train_skipped = _build_split_annotations(train_names, csv_map)
    test_annotations, test_skipped = _build_split_annotations(test_names, csv_map)

    _write_annotations(args.train_output, train_annotations)
    _write_annotations(args.test_output, test_annotations)

    print(f"Wrote train annotations: {args.train_output} ({len(train_annotations)} lines)")
    print(f"Wrote test annotations:  {args.test_output} ({len(test_annotations)} lines)")
    print(f"Skipped train entries not in anomaly CSV: {len(train_skipped)}")
    print(f"Skipped test entries not in anomaly CSV:  {len(test_skipped)}")


if __name__ == "__main__":
    main()
