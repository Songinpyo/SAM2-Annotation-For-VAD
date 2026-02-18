import argparse
import json
import os

from core.io.instance_metadata import import_instance_metadata


def _parse_prompt_frames(txt_path):
    per_entity_frames = {}

    with open(txt_path, 'r', encoding='utf-8') as f:
        for line_num, raw in enumerate(f, 1):
            line = raw.strip()
            if not line:
                continue

            parts = [p.strip() for p in line.split(',')]
            if len(parts) < 3:
                raise ValueError(f"Invalid TXT at line {line_num}: {raw!r}")

            frame = int(parts[0])
            entity_id = parts[1]
            ann_type = parts[2]

            if frame < 0 or ann_type == 'text':
                continue

            per_entity_frames.setdefault(entity_id, []).append(frame)

    ranges = {}
    for entity_id, frames in per_entity_frames.items():
        if not frames:
            ranges[entity_id] = (None, None)
        else:
            ranges[entity_id] = (min(frames), max(frames))
    return ranges


def _to_int_or_none(value):
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip() == "":
        return None
    try:
        return int(value)
    except Exception:
        return None


def _split_into_spans(frames_sorted):
    if not frames_sorted:
        return []

    spans = []
    start = frames_sorted[0]
    prev = frames_sorted[0]
    for frame in frames_sorted[1:]:
        if frame == prev + 1:
            prev = frame
            continue
        spans.append((start, prev))
        start = frame
        prev = frame
    spans.append((start, prev))
    return spans


def compute_runnable_spans(txt_path, sidecar_path):
    prompt_ranges = _parse_prompt_frames(txt_path)

    sidecar = None
    if sidecar_path and os.path.exists(sidecar_path):
        sidecar = import_instance_metadata(sidecar_path)

    instances = (sidecar or {}).get('entity_timeline', {}) if isinstance(sidecar, dict) else {}
    notes = (sidecar or {}).get('entity_notes', {}) if isinstance(sidecar, dict) else {}

    all_entity_ids = set(prompt_ranges.keys())
    if isinstance(instances, dict):
        all_entity_ids.update(instances.keys())
    if isinstance(notes, dict):
        all_entity_ids.update(notes.keys())

    result = {
        'txt_path': txt_path,
        'sidecar_path': sidecar_path if sidecar_path else None,
        'entities': {},
    }

    entities_out = result.get('entities')
    if not isinstance(entities_out, dict):
        entities_out = {}
        result['entities'] = entities_out

    for entity_id in sorted(all_entity_ids):
        prompt_min, prompt_max = prompt_ranges.get(entity_id, (None, None))

        timeline = instances.get(entity_id, {}) if isinstance(instances, dict) else {}
        enter_frame = _to_int_or_none(timeline.get('enter_frame') if isinstance(timeline, dict) else None)
        exit_frame = _to_int_or_none(timeline.get('exit_frame') if isinstance(timeline, dict) else None)

        if enter_frame is None:
            enter_frame = prompt_min
        if exit_frame is None:
            exit_frame = prompt_max

        missing_frames_raw = []
        if isinstance(timeline, dict) and isinstance(timeline.get('missing_frames'), list):
            missing_frames_raw = timeline.get('missing_frames', [])
        missing_frames = set()
        for value in missing_frames_raw:
            frame_int = _to_int_or_none(value)
            if frame_int is not None and frame_int >= 0:
                missing_frames.add(frame_int)

        runnable_frames_sorted = []
        if enter_frame is not None and exit_frame is not None and enter_frame <= exit_frame:
            runnable_frames_sorted = [
                f for f in range(enter_frame, exit_frame + 1)
                if f not in missing_frames
            ]

        spans = _split_into_spans(runnable_frames_sorted)

        entities_out[entity_id] = {
            'prompt_min_frame': prompt_min,
            'prompt_max_frame': prompt_max,
            'enter_frame': enter_frame,
            'exit_frame': exit_frame,
            'missing_frames_count': len(missing_frames),
            'runnable_frames_count': len(runnable_frames_sorted),
            'spans': [{'start': s, 'end': e} for (s, e) in spans],
        }

    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Preview Tracking-and-SAM2 runnable frame spans per entity. "
            "Reads prompt TXT and optional *.instances.json sidecar."
        )
    )
    parser.add_argument('txt', help='Path to exported prompt TXT')
    parser.add_argument('--sidecar', default=None, help='Path to *.instances.json (optional)')
    parser.add_argument('--json', action='store_true', help='Print machine-readable JSON')
    args = parser.parse_args()

    txt_path = args.txt
    if not os.path.exists(txt_path):
        raise FileNotFoundError(txt_path)

    sidecar_path = args.sidecar
    if sidecar_path is None:
        candidate = os.path.splitext(txt_path)[0] + '.instances.json'
        if os.path.exists(candidate):
            sidecar_path = candidate

    payload = compute_runnable_spans(txt_path, sidecar_path)
    if args.json:
        print(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True))
        return 0

    print(f"TXT: {payload['txt_path']}")
    if payload['sidecar_path']:
        print(f"Sidecar: {payload['sidecar_path']}")
    else:
        print("Sidecar: (missing)")

    entities = payload.get('entities')
    if not isinstance(entities, dict):
        entities = {}

    for entity_id, info in entities.items():
        prompt_min = info.get('prompt_min_frame')
        prompt_max = info.get('prompt_max_frame')
        enter_frame = info.get('enter_frame')
        exit_frame = info.get('exit_frame')
        spans = info.get('spans', [])

        prompt_range_str = f"{prompt_min}..{prompt_max}" if prompt_min is not None else "(none)"
        valid_range_str = f"{enter_frame}..{exit_frame}" if enter_frame is not None else "(none)"
        spans_str = ', '.join([f"{s['start']}..{s['end']}" for s in spans]) if spans else "(none)"

        line = (
            f"- {entity_id}: prompts={prompt_range_str} valid={valid_range_str} "
            f"missing={info.get('missing_frames_count', 0)} spans={spans_str}"
        )
        print(line)

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
