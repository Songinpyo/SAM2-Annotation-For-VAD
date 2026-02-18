import json
import os


def _normalize_missing_frames(missing_frames):
    normalized = []
    for value in missing_frames or []:
        frame = int(value)
        if frame >= 0:
            normalized.append(frame)
    return sorted(set(normalized))


def _normalize_entity_ids(values):
    ids = []
    if isinstance(values, list):
        for value in values:
            if isinstance(value, str):
                entity_id = value.strip()
                if entity_id:
                    ids.append(entity_id)
    return sorted(set(ids))


def _normalize_event_data(raw):
    def to_int_or_none(value):
        if value is None:
            return None
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            token = value.strip()
            if not token:
                return None
            try:
                return int(token)
            except Exception:
                return None
        return None

    start_frame = None
    end_frame = None
    perp_text = ""
    verb_text = ""
    subj_text = ""
    loca_text = ""
    perp_entity_ids = []
    subj_entity_ids = []

    if isinstance(raw, dict):
        segment = raw.get('segment', {})
        if isinstance(segment, dict):
            start_frame = segment.get('start_frame')
            end_frame = segment.get('end_frame')

        start_frame = to_int_or_none(start_frame)
        end_frame = to_int_or_none(end_frame)
        if start_frame is not None and end_frame is not None and start_frame > end_frame:
            start_frame, end_frame = end_frame, start_frame

        text_map = raw.get('text', {})
        if isinstance(text_map, dict):
            perp_text = str(text_map.get('perp', '')).strip()
            verb_text = str(text_map.get('verb', '')).strip()
            subj_text = str(text_map.get('subj', '')).strip()
            loca_text = str(text_map.get('loca', '')).strip()

        assignments = raw.get('assignments', {})
        if isinstance(assignments, dict):
            perp_entity_ids = _normalize_entity_ids(assignments.get('perp_entity_ids', []))
            subj_entity_ids = _normalize_entity_ids(assignments.get('subj_entity_ids', []))

    return {
        'segment_start_frame': start_frame,
        'segment_end_frame': end_frame,
        'perp_text': perp_text,
        'verb_text': verb_text,
        'subj_text': subj_text,
        'loca_text': loca_text,
        'perp_entity_ids': perp_entity_ids,
        'subj_entity_ids': subj_entity_ids,
    }


def _normalize_internal_event(raw):
    if isinstance(raw, dict) and (
        'segment_start_frame' in raw
        or 'segment_end_frame' in raw
        or 'perp_text' in raw
        or 'verb_text' in raw
        or 'subj_text' in raw
        or 'loca_text' in raw
    ):
        normalized = {
            'segment_start_frame': raw.get('segment_start_frame'),
            'segment_end_frame': raw.get('segment_end_frame'),
            'perp_text': str(raw.get('perp_text', '')).strip(),
            'verb_text': str(raw.get('verb_text', '')).strip(),
            'subj_text': str(raw.get('subj_text', '')).strip(),
            'loca_text': str(raw.get('loca_text', '')).strip(),
            'perp_entity_ids': _normalize_entity_ids(raw.get('perp_entity_ids', [])),
            'subj_entity_ids': _normalize_entity_ids(raw.get('subj_entity_ids', [])),
        }

        start_frame = normalized.get('segment_start_frame')
        end_frame = normalized.get('segment_end_frame')
        if not isinstance(start_frame, int):
            start_frame = None
        if not isinstance(end_frame, int):
            end_frame = None
        if start_frame is not None and end_frame is not None and start_frame > end_frame:
            start_frame, end_frame = end_frame, start_frame
        normalized['segment_start_frame'] = start_frame
        normalized['segment_end_frame'] = end_frame
        return normalized

    return _normalize_event_data(raw)


def _is_event_empty(event_data):
    if not isinstance(event_data, dict):
        return True
    return (
        event_data.get('segment_start_frame') is None
        and event_data.get('segment_end_frame') is None
        and not str(event_data.get('perp_text', '')).strip()
        and not str(event_data.get('verb_text', '')).strip()
        and not str(event_data.get('subj_text', '')).strip()
        and not str(event_data.get('loca_text', '')).strip()
        and not event_data.get('perp_entity_ids')
        and not event_data.get('subj_entity_ids')
    )


def build_instance_metadata_payload(metadata_state):
    instances = {}

    if not isinstance(metadata_state, dict):
        return {
            'schema_version': '2.1',
            'frame_indexing': '0-based',
            'events': [],
            'instances': {},
        }

    entity_notes = metadata_state.get('entity_notes', {})
    entity_timeline = metadata_state.get('entity_timeline', {})

    all_entity_ids = metadata_state.get('all_entity_ids', [])

    entity_ids = set()
    if isinstance(all_entity_ids, list):
        for entity_id in all_entity_ids:
            if isinstance(entity_id, str) and entity_id.strip():
                entity_ids.add(entity_id.strip())
    if isinstance(entity_notes, dict):
        entity_ids.update(entity_notes.keys())
    if isinstance(entity_timeline, dict):
        entity_ids.update(entity_timeline.keys())

    for entity_id in sorted(entity_ids):
        note = ""
        if isinstance(entity_notes, dict) and entity_id in entity_notes:
            note = str(entity_notes[entity_id]).strip()

        timeline = {}
        if isinstance(entity_timeline, dict):
            raw_timeline = entity_timeline.get(entity_id, {})
            if isinstance(raw_timeline, dict):
                timeline = raw_timeline
        enter_frame = timeline.get('enter_frame')
        exit_frame = timeline.get('exit_frame')
        missing_frames = _normalize_missing_frames(timeline.get('missing_frames', []))

        if enter_frame is not None:
            enter_frame = int(enter_frame)
        if exit_frame is not None:
            exit_frame = int(exit_frame)

        if not note and enter_frame is None and exit_frame is None and not missing_frames:
            continue

        instance_obj = {
            'text': note,
            'enter_frame': enter_frame,
            'exit_frame': exit_frame,
            'missing_frames': missing_frames,
        }

        instances[entity_id] = instance_obj

    events_raw = metadata_state.get('events_data', [])
    if isinstance(events_raw, dict):
        events_iter = [events_raw]
    elif isinstance(events_raw, list):
        events_iter = events_raw
    else:
        events_iter = []

    events_payload = []
    for raw in events_iter:
        normalized_event = _normalize_internal_event(raw)
        if _is_event_empty(normalized_event):
            continue
        events_payload.append({
            'segment': {
                'start_frame': normalized_event.get('segment_start_frame'),
                'end_frame': normalized_event.get('segment_end_frame'),
            },
            'text': {
                'perp': normalized_event.get('perp_text', ''),
                'verb': normalized_event.get('verb_text', ''),
                'subj': normalized_event.get('subj_text', ''),
                'loca': normalized_event.get('loca_text', ''),
            },
            'assignments': {
                'perp_entity_ids': _normalize_entity_ids(normalized_event.get('perp_entity_ids', [])),
                'subj_entity_ids': _normalize_entity_ids(normalized_event.get('subj_entity_ids', [])),
            },
        })

    payload = {
        'schema_version': '2.1',
        'frame_indexing': '0-based',
        'events': events_payload,
        'instances': instances,
    }

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

    events_data = []
    if isinstance(payload, dict) and isinstance(payload.get('events'), list):
        for raw_event in payload.get('events', []):
            events_data.append(_normalize_event_data(raw_event))
    elif isinstance(payload, dict) and isinstance(payload.get('event'), dict):
        events_data = [_normalize_event_data(payload.get('event', {}))]

    if isinstance(payload, dict) and not events_data:
        legacy_verb = str(payload.get('anomaly_type', '')).strip()
        legacy_loca = str(payload.get('scene_location', '')).strip()

        participants = payload.get('participants', []) if isinstance(payload.get('participants'), list) else []
        perp_ids = []
        subj_ids = []
        for item in participants:
            if not isinstance(item, dict):
                continue
            entity_id = str(item.get('entity_id', '')).strip()
            role = str(item.get('role', '')).strip().lower()
            if not entity_id:
                continue
            if role == 'perpetrator':
                perp_ids.append(entity_id)
            elif role == 'victim_target':
                subj_ids.append(entity_id)

        events_data = [{
            'segment_start_frame': None,
            'segment_end_frame': None,
            'perp_text': '',
            'verb_text': legacy_verb,
            'subj_text': '',
            'loca_text': legacy_loca,
            'perp_entity_ids': _normalize_entity_ids(perp_ids),
            'subj_entity_ids': _normalize_entity_ids(subj_ids),
        }]

    if isinstance(payload, dict) and isinstance(payload.get('instances'), dict):
        for entity_id, raw in payload['instances'].items():
            if not isinstance(raw, dict):
                continue

            note_value = raw.get('text', raw.get('appearance_caption', ''))
            note = str(note_value).strip()
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
                timeline_empty = True
            else:
                timeline_empty = False

            if not timeline_empty:
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
        'events_data': events_data,
        'entity_notes': entity_notes,
        'entity_timeline': entity_timeline,
    }
