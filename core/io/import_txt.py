import re

def import_annotations(txt_path, video_width, video_height):
    """
    Import annotations from .txt file
    Returns list of annotation dicts
    """
    annotations = []

    with open(txt_path, 'r') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue

            try:
                ann = parse_line(line, video_width, video_height)
                annotations.append(ann)
            except Exception as e:
                raise ValueError(f"Error parsing line {line_num}: {e}")

    return annotations


def parse_line(line, video_width, video_height):
    """Parse a single annotation line"""
    parts = [p.strip() for p in line.split(',')]

    if len(parts) < 4:
        raise ValueError(f"Not enough fields: {line}")

    frame = int(parts[0])
    entity_id = parts[1]
    ann_type = parts[2]

    # validate id
    pattern = r'^(actor|subject|related)[0-9]$'
    if not re.match(pattern, entity_id):
        raise ValueError(f"Invalid entity id: {entity_id}")

    # parse coords
    if ann_type == 'bbox':
        if len(parts) != 7:
            raise ValueError(f"bbox should have 4 coords")
        coords_rel = [float(parts[i]) for i in range(3, 7)]
        coords_pix = to_pixel_coords(coords_rel, video_width, video_height, 'bbox')

    elif ann_type in ['pos_point', 'neg_point']:
        if len(parts) != 5:
            raise ValueError(f"{ann_type} should have 2 coords")
        coords_rel = [float(parts[i]) for i in range(3, 5)]
        coords_pix = to_pixel_coords(coords_rel, video_width, video_height, 'point')

    elif ann_type == 'text':
        # Text annotation: coords are the text string (everything after type field)
        # Rejoin in case the text contains commas
        text = ', '.join(parts[3:]) if len(parts) > 3 else ""
        coords_pix = [text]

    else:
        raise ValueError(f"Unknown type: {ann_type}")

    return {
        'frame': frame,
        'id': entity_id,
        'type': ann_type,
        'coords': coords_pix
    }


def to_pixel_coords(coords_rel, width, height, coord_type):
    """Convert relative [0,1] coords to pixel coords"""
    if coord_type == 'bbox':
        x_rel, y_rel, w_rel, h_rel = coords_rel
        x = x_rel * width
        y = y_rel * height
        w = w_rel * width
        h = h_rel * height
        return [x, y, w, h]

    elif coord_type == 'point':
        x_rel, y_rel = coords_rel
        x = x_rel * width
        y = y_rel * height
        return [x, y]

    else:
        raise ValueError(f"Unknown coord_type: {coord_type}")
