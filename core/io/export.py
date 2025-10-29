import re
import os

def export_annotations(annotations, video_width, video_height, output_path):
    """
    Export annotations to .txt file with relative coords

    annotations: list of dicts with keys: frame, id, type, coords
    coords are in pixel values
    """
    lines = []

    for ann in annotations:
        frame = ann['frame']
        entity_id = ann['id']
        ann_type = ann['type']
        coords_pix = ann['coords']

        # convert to relative coords
        coords_rel = to_relative_coords(coords_pix, video_width, video_height, ann_type)

        # format: frame, id, type, coords...
        if ann_type == 'text':
            # Text coords are strings, format differently
            coord_str = coords_rel[0] if coords_rel else ""
        else:
            # Numeric coords, format as floats
            coord_str = ', '.join([f'{c:.6f}' for c in coords_rel])

        line = f"{frame}, {entity_id}, {ann_type}, {coord_str}"
        lines.append(line)

    # write to file
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        f.write('\n'.join(lines))


def to_relative_coords(coords, width, height, coord_type):
    """Convert pixel coords to [0,1] relative coords"""
    if coord_type == 'bbox':
        x, y, w, h = coords
        x_rel = max(0.0, min(1.0, x / width))
        y_rel = max(0.0, min(1.0, y / height))
        w_rel = max(0.0, min(1.0, w / width))
        h_rel = max(0.0, min(1.0, h / height))
        return [x_rel, y_rel, w_rel, h_rel]

    elif coord_type in ['pos_point', 'neg_point']:
        x, y = coords
        x_rel = max(0.0, min(1.0, x / width))
        y_rel = max(0.0, min(1.0, y / height))
        return [x_rel, y_rel]

    elif coord_type == 'text':
        # Text coords are already strings, return as-is
        return coords

    else:
        raise ValueError(f"Unknown coord_type: {coord_type}")


def validate_annotations(annotations):
    """
    Validate annotations before export
    Returns (is_valid, errors)
    """
    errors = []

    # check for duplicate bboxes per (frame, id)
    bbox_keys = set()

    for ann in annotations:
        frame = ann['frame']
        entity_id = ann['id']
        ann_type = ann['type']

        # check frame is int (allow -1 for metadata/text)
        if not isinstance(frame, int):
            errors.append(f"Frame {frame} is not an integer")

        # check id format
        pattern = r'^(actor|subject|related)[0-9]$'
        if not re.match(pattern, entity_id):
            errors.append(f"Invalid id format: {entity_id}")

        # check bbox uniqueness
        if ann_type == 'bbox':
            key = (frame, entity_id)
            if key in bbox_keys:
                errors.append(f"Duplicate bbox for frame={frame}, id={entity_id}")
            bbox_keys.add(key)

    return len(errors) == 0, errors


def generate_statistics(annotations):
    """Generate stats report"""
    frames = set()
    entities = set()
    per_entity = {}

    for ann in annotations:
        frame = ann['frame']
        entity_id = ann['id']
        ann_type = ann['type']

        # Skip metadata (frame -1) for frame counting
        if frame >= 0:
            frames.add(frame)

        entities.add(entity_id)

        if entity_id not in per_entity:
            per_entity[entity_id] = {'bbox': 0, 'pos_point': 0, 'neg_point': 0, 'text': 0}

        if ann_type in per_entity[entity_id]:
            per_entity[entity_id][ann_type] += 1

    return {
        'total_frames': len(frames),
        'total_annotations': len(annotations),
        'entities': sorted(list(entities)),
        'per_entity': per_entity
    }
