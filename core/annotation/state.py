import copy

class AnnotationState:
    def __init__(self):
        self.current_video = None
        self.current_anchors = []
        self.current_anchor_idx = 0
        self.current_dt = 1
        self.video_width = 1920
        self.video_height = 1080

        # annotations: {frame: {entity_id: {bbox, pos_points, neg_points}}}
        self.annotations = {}

        # entity notes: {entity_id: "text note"}
        self.entity_notes = {}

        # undo/redo
        self.history = []
        self.history_idx = -1

    def set_video(self, video_name, anchors, dt, width, height):
        self.current_video = video_name
        self.current_anchors = anchors
        self.current_dt = dt
        self.video_width = width
        self.video_height = height
        self.current_anchor_idx = 0

    def add_bbox(self, frame, entity_id, coords):
        """Add or update bbox for entity at frame"""
        if frame not in self.annotations:
            self.annotations[frame] = {}

        if entity_id not in self.annotations[frame]:
            self.annotations[frame][entity_id] = {
                'bbox': None,
                'pos_points': [],
                'neg_points': []
            }

        self.annotations[frame][entity_id]['bbox'] = coords
        self.save_history()

    def add_point(self, frame, entity_id, coords, point_type):
        """Add pos_point or neg_point"""
        if frame not in self.annotations:
            self.annotations[frame] = {}

        if entity_id not in self.annotations[frame]:
            self.annotations[frame][entity_id] = {
                'bbox': None,
                'pos_points': [],
                'neg_points': []
            }

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

        self.save_history()

    def save_history(self):
        """Save current state to history"""
        # truncate future history if we're in the middle
        if self.history_idx < len(self.history) - 1:
            self.history = self.history[:self.history_idx + 1]

        # deep copy current annotations
        snapshot = copy.deepcopy(self.annotations)
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
            self.annotations = copy.deepcopy(self.history[self.history_idx])
            return True
        return False

    def redo(self):
        """Redo last undone action"""
        if self.history_idx < len(self.history) - 1:
            self.history_idx += 1
            self.annotations = copy.deepcopy(self.history[self.history_idx])
            return True
        return False

    def import_from_list(self, annotations):
        """Load annotations from import"""
        self.annotations = {}
        self.entity_notes = {}

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
                self.annotations[frame][entity_id] = {
                    'bbox': None,
                    'pos_points': [],
                    'neg_points': []
                }

            if ann_type == 'bbox':
                self.annotations[frame][entity_id]['bbox'] = coords
            elif ann_type == 'pos_point':
                self.annotations[frame][entity_id]['pos_points'].append(coords)
            elif ann_type == 'neg_point':
                self.annotations[frame][entity_id]['neg_points'].append(coords)

        self.save_history()

    def export_to_list(self):
        """Convert to export format"""
        result = []

        # Export entity notes as frame -1 with type 'text'
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
