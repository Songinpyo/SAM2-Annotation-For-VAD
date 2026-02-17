import json
import os


def _normalize_missing_frames(missing_frames):
    normalized = []
    for value in missing_frames or []:
        frame = int(value)
        if frame >= 0:
            normalized.append(frame)
    return sorted(set(normalized))


def build_instance_metadata_payload(entity_notes, entity_timeline, video_caption=""):
    instances = {}
    entity_ids = set((entity_notes or {}).keys()) | set((entity_timeline or {}).keys())

    for entity_id in sorted(entity_ids):
        note = ""
        if entity_id in (entity_notes or {}):
            note = str((entity_notes or {})[entity_id]).strip()

        timeline = (entity_timeline or {}).get(entity_id, {})
        enter_frame = timeline.get('enter_frame')
        exit_frame = timeline.get('exit_frame')
        missing_frames = _normalize_missing_frames(timeline.get('missing_frames', []))

        if enter_frame is not None:
            enter_frame = int(enter_frame)
        if exit_frame is not None:
            exit_frame = int(exit_frame)

        if not note and enter_frame is None and exit_frame is None and not missing_frames:
            continue

        instances[entity_id] = {
            'text': note,
            'enter_frame': enter_frame,
            'exit_frame': exit_frame,
            'missing_frames': missing_frames,
        }

    payload = {
        'schema_version': '1.0',
        'frame_indexing': '0-based',
        'instances': instances,
    }

    caption_text = ""
    if video_caption and str(video_caption).strip():
        caption_text = str(video_caption).strip()
    if caption_text:
        payload['video_caption'] = caption_text

    return payload


def export_instance_metadata(payload, output_path):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def import_instance_metadata(input_path):
    with open(input_path, 'r', encoding='utf-8') as f:
        payload = json.load(f)

    entity_notes = {}
    entity_timeline = {}
    video_caption = ""

    if isinstance(payload, dict) and payload.get('video_caption') is not None:
        video_caption = str(payload.get('video_caption', '')).strip()

    if isinstance(payload, dict) and isinstance(payload.get('instances'), dict):
        for entity_id, raw in payload['instances'].items():
            if not isinstance(raw, dict):
                continue

            note = str(raw.get('text', '')).strip()
            if note:
                entity_notes[entity_id] = note

            enter_frame = raw.get('enter_frame')
            exit_frame = raw.get('exit_frame')
            missing_frames = _normalize_missing_frames(raw.get('missing_frames', []))

            if enter_frame is not None:
                enter_frame = int(enter_frame)
            if exit_frame is not None:
                exit_frame = int(exit_frame)

            if enter_frame is None and exit_frame is None and not missing_frames:
                continue

            entity_timeline[entity_id] = {
                'enter_frame': enter_frame,
                'exit_frame': exit_frame,
                'missing_frames': missing_frames,
            }
    else:
        notes_map = payload.get('entity_notes', {}) if isinstance(payload, dict) else {}
        timeline_map = payload.get('entity_timeline', {}) if isinstance(payload, dict) else {}

        if isinstance(notes_map, dict):
            for entity_id, note in notes_map.items():
                note_text = str(note).strip()
                if note_text:
                    entity_notes[entity_id] = note_text

        if isinstance(timeline_map, dict):
            for entity_id, timeline in timeline_map.items():
                if not isinstance(timeline, dict):
                    continue
                enter_frame = timeline.get('enter_frame')
                exit_frame = timeline.get('exit_frame')
                missing_frames = _normalize_missing_frames(timeline.get('missing_frames', []))
                if enter_frame is not None:
                    enter_frame = int(enter_frame)
                if exit_frame is not None:
                    exit_frame = int(exit_frame)
                if enter_frame is None and exit_frame is None and not missing_frames:
                    continue
                entity_timeline[entity_id] = {
                    'enter_frame': enter_frame,
                    'exit_frame': exit_frame,
                    'missing_frames': missing_frames,
                }

    return {
        'video_caption': video_caption,
        'entity_notes': entity_notes,
        'entity_timeline': entity_timeline,
    }
