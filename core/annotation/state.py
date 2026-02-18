import copy

class AnnotationState:
    def __init__(self):
        self.current_video = None
        self.current_anchors = []
        self.current_anchor_idx = 0
        self.current_dt = 1
        self.video_width = 1920
        self.video_height = 1080

        self.events_data = []

        # annotations: {frame: {entity_id: {bbox, pos_points, neg_points}}}
        self.annotations = {}

        # entity notes: {entity_id: "text note"}
        self.entity_notes = {}

        self.entity_timeline = {}

        # undo/redo
        self.history = []
        self.history_idx = -1

    def _empty_entity_data(self):
        return {
            'bbox': None,
            'pos_points': [],
            'neg_points': []
        }

    def _ensure_entity(self, frame, entity_id):
        if frame not in self.annotations:
            self.annotations[frame] = {}
        if entity_id not in self.annotations[frame]:
            self.annotations[frame][entity_id] = self._empty_entity_data()

    def _is_entity_empty(self, entity_data):
        return (
            entity_data.get('bbox') is None
            and not entity_data.get('pos_points')
            and not entity_data.get('neg_points')
        )

    def _build_snapshot(self):
        return {
            'annotations': copy.deepcopy(self.annotations),
            'events_data': copy.deepcopy(self.events_data),
            'entity_notes': copy.deepcopy(self.entity_notes),
            'entity_timeline': copy.deepcopy(self.entity_timeline),
        }

    def _restore_snapshot(self, snapshot):
        self.annotations = copy.deepcopy(snapshot.get('annotations', {}))
        self.events_data = self._normalize_events_data(snapshot.get('events_data', []))
        self.entity_notes = copy.deepcopy(snapshot.get('entity_notes', {}))
        self.entity_timeline = copy.deepcopy(snapshot.get('entity_timeline', {}))

    def _empty_event_data(self):
        return {
            'segment_start_frame': None,
            'segment_end_frame': None,
            'perp_text': "",
            'verb_text': "",
            'subj_text': "",
            'loca_text': "",
            'perp_entity_ids': [],
            'subj_entity_ids': [],
        }

    def _normalize_entity_ids(self, values):
        ids = []
        if isinstance(values, list):
            for value in values:
                if isinstance(value, str):
                    entity_id = value.strip()
                    if entity_id:
                        ids.append(entity_id)
        return sorted(set(ids))

    def _normalize_event_data(self, event_data):
        start_frame = None
        end_frame = None
        perp_text = ""
        verb_text = ""
        subj_text = ""
        loca_text = ""
        perp_entity_ids = []
        subj_entity_ids = []

        if isinstance(event_data, dict):
            start_frame = event_data.get('segment_start_frame')
            end_frame = event_data.get('segment_end_frame')

            if start_frame is not None:
                start_frame = int(start_frame)
            if end_frame is not None:
                end_frame = int(end_frame)
            if start_frame is not None and end_frame is not None and start_frame > end_frame:
                start_frame, end_frame = end_frame, start_frame

            for key in ['perp_text', 'verb_text', 'subj_text', 'loca_text']:
                value = event_data.get(key, "")
                if value and str(value).strip():
                    if key == 'perp_text':
                        perp_text = str(value).strip()
                    elif key == 'verb_text':
                        verb_text = str(value).strip()
                    elif key == 'subj_text':
                        subj_text = str(value).strip()
                    elif key == 'loca_text':
                        loca_text = str(value).strip()

            perp_entity_ids = self._normalize_entity_ids(event_data.get('perp_entity_ids', []))
            subj_entity_ids = self._normalize_entity_ids(event_data.get('subj_entity_ids', []))

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

    def _normalize_events_data(self, events_data):
        if isinstance(events_data, dict):
            return [self._normalize_event_data(events_data)]

        result = []
        if isinstance(events_data, list):
            for event_data in events_data:
                if isinstance(event_data, dict):
                    result.append(self._normalize_event_data(event_data))
        return result

    def _is_event_empty(self, event_data):
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

    def _empty_timeline_data(self):
        return {
            'enter_frame': None,
            'exit_frame': None,
            'missing_frames': []
        }

    def _normalize_missing_frames(self, missing_frames):
        normalized = []
        for frame in missing_frames or []:
            frame_int = int(frame)
            if frame_int >= 0:
                normalized.append(frame_int)
        return sorted(set(normalized))

    def set_video(self, video_name, anchors, dt, width, height):
        self.current_video = video_name
        self.current_anchors = anchors
        self.current_dt = dt
        self.video_width = width
        self.video_height = height
        self.current_anchor_idx = 0

    def add_bbox(self, frame, entity_id, coords):
        """Add or update bbox for entity at frame"""
        self._ensure_entity(frame, entity_id)

        self.annotations[frame][entity_id]['bbox'] = coords
        self.save_history()

    def add_point(self, frame, entity_id, coords, point_type):
        """Add pos_point or neg_point"""
        self._ensure_entity(frame, entity_id)

        if point_type == 'pos_point':
            self.annotations[frame][entity_id]['pos_points'].append(coords)
        elif point_type == 'neg_point':
            self.annotations[frame][entity_id]['neg_points'].append(coords)

        self.save_history()

    def get_annotations_for_frame(self, frame):
        """Get all annotations for a specific frame"""
        return self.annotations.get(frame, {})

    def carry_forward_bbox(self, from_frame, to_frame, entity_id):
        """Copy bbox from previous frame to current"""
        if from_frame in self.annotations:
            if entity_id in self.annotations[from_frame]:
                bbox = self.annotations[from_frame][entity_id].get('bbox')
                if bbox:
                    self.add_bbox(to_frame, entity_id, bbox.copy())
                    return True
        return False

    def delete_annotation(self, frame, entity_id, ann_type=None):
        """Delete annotation(s) for entity at frame"""
        if frame not in self.annotations:
            return

        if entity_id not in self.annotations[frame]:
            return

        if ann_type is None:
            # delete all
            del self.annotations[frame][entity_id]
        elif ann_type == 'bbox':
            self.annotations[frame][entity_id]['bbox'] = None
        elif ann_type == 'pos_point':
            self.annotations[frame][entity_id]['pos_points'] = []
        elif ann_type == 'neg_point':
            self.annotations[frame][entity_id]['neg_points'] = []

        if entity_id in self.annotations.get(frame, {}):
            if self._is_entity_empty(self.annotations[frame][entity_id]):
                del self.annotations[frame][entity_id]
        if frame in self.annotations and not self.annotations[frame]:
            del self.annotations[frame]

        self.save_history()

    def save_history(self):
        """Save current state to history"""
        # truncate future history if we're in the middle
        if self.history_idx < len(self.history) - 1:
            self.history = self.history[:self.history_idx + 1]

        snapshot = self._build_snapshot()

        if self.history and self.history[self.history_idx] == snapshot:
            return

        self.history.append(snapshot)
        self.history_idx += 1

        # keep history size reasonable
        if len(self.history) > 50:
            self.history.pop(0)
            self.history_idx -= 1

    def undo(self):
        """Undo last action"""
        if self.history_idx > 0:
            self.history_idx -= 1
            self._restore_snapshot(self.history[self.history_idx])
            return True
        return False

    def redo(self):
        """Redo last undone action"""
        if self.history_idx < len(self.history) - 1:
            self.history_idx += 1
            self._restore_snapshot(self.history[self.history_idx])
            return True
        return False

    def import_from_list(self, annotations):
        """Load annotations from import"""
        self.annotations = {}
        self.entity_notes = {}
        self.entity_timeline = {}
        self.events_data = []

        for ann in annotations:
            frame = ann['frame']
            entity_id = ann['id']
            ann_type = ann['type']
            coords = ann['coords']

            # Frame -1 is reserved for metadata (entity notes)
            if frame == -1 and ann_type == 'text':
                self.entity_notes[entity_id] = coords[0] if coords else ""
                continue

            if frame not in self.annotations:
                self.annotations[frame] = {}

            if entity_id not in self.annotations[frame]:
                self.annotations[frame][entity_id] = self._empty_entity_data()

            if ann_type == 'bbox':
                self.annotations[frame][entity_id]['bbox'] = coords
            elif ann_type == 'pos_point':
                self.annotations[frame][entity_id]['pos_points'].append(coords)
            elif ann_type == 'neg_point':
                self.annotations[frame][entity_id]['neg_points'].append(coords)

        self.save_history()

    def export_to_list(self, include_text=True):
        """Convert to export format"""
        result = []

        if include_text:
            for entity_id in sorted(self.entity_notes.keys()):
                result.append({
                    'frame': -1,
                    'id': entity_id,
                    'type': 'text',
                    'coords': [self.entity_notes[entity_id]]  # coords as list with text
                })

        # Export regular annotations
        for frame in sorted(self.annotations.keys()):
            for entity_id in sorted(self.annotations[frame].keys()):
                entity_data = self.annotations[frame][entity_id]

                # bbox
                if entity_data['bbox']:
                    result.append({
                        'frame': frame,
                        'id': entity_id,
                        'type': 'bbox',
                        'coords': entity_data['bbox']
                    })

                # pos points
                for pt in entity_data['pos_points']:
                    result.append({
                        'frame': frame,
                        'id': entity_id,
                        'type': 'pos_point',
                        'coords': pt
                    })

                # neg points
                for pt in entity_data['neg_points']:
                    result.append({
                        'frame': frame,
                        'id': entity_id,
                        'type': 'neg_point',
                        'coords': pt
                    })

        return result

    def get_active_entities(self):
        """Get list of all entity ids that have annotations"""
        entities = set()
        for frame_data in self.annotations.values():
            entities.update(frame_data.keys())
        return sorted(list(entities))

    def set_entity_note(self, entity_id, note):
        """Set text note for an entity"""
        if note and note.strip():
            self.entity_notes[entity_id] = note.strip()
        elif entity_id in self.entity_notes:
            del self.entity_notes[entity_id]
        self.save_history()

    def get_entity_note(self, entity_id):
        """Get text note for an entity"""
        return self.entity_notes.get(entity_id, "")

    def set_event_data(self, event_data, index=0):
        events = self._normalize_events_data(self.events_data)
        while len(events) <= index:
            events.append(self._normalize_event_data({}))
        events[index] = self._normalize_event_data(event_data)
        self.events_data = events
        self.save_history()

    def get_event_data(self, index=0):
        events = self._normalize_events_data(self.events_data)
        if 0 <= index < len(events):
            return copy.deepcopy(events[index])
        return self._empty_event_data()

    def set_events_data(self, events_data):
        self.events_data = self._normalize_events_data(events_data)
        self.save_history()

    def get_events_data(self):
        return copy.deepcopy(self._normalize_events_data(self.events_data))

    def set_entity_timeline(
        self,
        entity_id,
        enter_frame,
        exit_frame,
        missing_frames
    ):
        timeline = copy.deepcopy(self.entity_timeline.get(entity_id, self._empty_timeline_data()))
        timeline['enter_frame'] = None if enter_frame is None else int(enter_frame)
        timeline['exit_frame'] = None if exit_frame is None else int(exit_frame)
        timeline['missing_frames'] = self._normalize_missing_frames(missing_frames)

        if (
            timeline.get('enter_frame') is None
            and timeline.get('exit_frame') is None
            and not timeline.get('missing_frames')
        ):
            if entity_id in self.entity_timeline:
                del self.entity_timeline[entity_id]
        else:
            self.entity_timeline[entity_id] = timeline

        self.save_history()

    def get_entity_timeline(self, entity_id):
        timeline = copy.deepcopy(self.entity_timeline.get(entity_id, self._empty_timeline_data()))
        timeline['missing_frames'] = self._normalize_missing_frames(timeline.get('missing_frames', []))
        return timeline

    def import_instance_metadata(
        self,
        entity_notes,
        entity_timeline,
        events_data=None,
    ):
        self.entity_notes = {}
        self.entity_timeline = {}
        self.events_data = self._normalize_events_data(events_data or [])

        for entity_id, note in (entity_notes or {}).items():
            if note and str(note).strip():
                self.entity_notes[entity_id] = str(note).strip()

        for entity_id, timeline in (entity_timeline or {}).items():
            enter_frame = timeline.get('enter_frame')
            exit_frame = timeline.get('exit_frame')
            missing_frames = self._normalize_missing_frames(timeline.get('missing_frames', []))

            if enter_frame is not None:
                enter_frame = int(enter_frame)
            if exit_frame is not None:
                exit_frame = int(exit_frame)

            if enter_frame is None and exit_frame is None and not missing_frames:
                continue

            self.entity_timeline[entity_id] = {
                'enter_frame': enter_frame,
                'exit_frame': exit_frame,
                'missing_frames': missing_frames,
            }

        self.save_history()

    def export_instance_metadata(self):
        notes = {}
        timeline_map = {}

        for entity_id in sorted(self.entity_notes.keys()):
            note = self.entity_notes[entity_id]
            if note and str(note).strip():
                notes[entity_id] = str(note).strip()

        for entity_id in sorted(self.entity_timeline.keys()):
            timeline = self.get_entity_timeline(entity_id)
            enter_frame = timeline.get('enter_frame')
            exit_frame = timeline.get('exit_frame')
            missing_frames = timeline.get('missing_frames', [])
            if enter_frame is None and exit_frame is None and not missing_frames:
                continue
            timeline_map[entity_id] = {
                'enter_frame': enter_frame,
                'exit_frame': exit_frame,
                'missing_frames': missing_frames,
            }

        return {
            'events_data': [
                event
                for event in self._normalize_events_data(self.events_data)
                if not self._is_event_empty(event)
            ],
            'all_entity_ids': self.get_all_entity_ids(),
            'entity_notes': notes,
            'entity_timeline': timeline_map,
        }

    def get_all_entity_ids(self):
        entities = set(self.get_active_entities())
        entities.update(self.entity_notes.keys())
        entities.update(self.entity_timeline.keys())
        for event_data in self._normalize_events_data(self.events_data):
            perp_ids = event_data.get('perp_entity_ids', [])
            if isinstance(perp_ids, list):
                entities.update(perp_ids)
            subj_ids = event_data.get('subj_entity_ids', [])
            if isinstance(subj_ids, list):
                entities.update(subj_ids)
        return sorted(entities)
