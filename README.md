# SAM2 Anomaly Annotation Tool

Annotation tool for anomaly detection datasets using Equal-Interval Seeding (EIS) strategy.

## Features

- EIS frame selection (K ∈ [3, 15])
- Multi-entity annotation (actor, subject, related)
- Entity notes support (optional text descriptions)
- Undo/Redo history
- Import/Resume from existing annotations
- Validation on export

## Installation

```bash
pip install -r requirements.txt
```

## Usage

Place 1fps converted videos in `data/ucf-crime/videos/` or `data/xd-violence/videos/`, then run:

```bash
python app/main.py
```

### Basic Workflow

1. Select dataset and video from left sidebar
2. Set run name (e.g., "v1" or "john_review")
3. Select entity (role + ID) and tool (bbox/pos_point/neg_point)
4. Draw annotations on frames
5. Optionally add text notes for entities
6. Navigate with A/D keys or timeline buttons
7. Export when done (Ctrl+S or button)

Note: Export saves current video only. Repeat for each video.

### Keyboard Shortcuts

Frame navigation:
- A/D: Previous/Next frame
- Ctrl+A/D: Previous/Next video
- F: Carry forward bbox

Entity selection:
- Q/W/E: Actor/Subject/Related
- 1-9, 0: ID 0-8, 9
- Z/X/C: BBox/Pos point/Neg point

Other:
- Ctrl+Z: Undo
- Ctrl+Shift+Z: Redo
- Ctrl+S: Export current video
- Delete: Remove selected annotation

## Output Format

Annotations are saved as text files with relative coordinates [0,1]:

```
-1, actor0, text, running away from explosion
60, actor0, bbox, 0.512300, 0.338900, 0.080000, 0.210000
60, actor0, pos_point, 0.560000, 0.410000
70, actor0, bbox, 0.530000, 0.345000, 0.078000, 0.205000
```

Format: `frame, entity_id, type, coordinates...`

Entity notes are stored as frame -1 with type 'text'.

## Configuration

Edit `configs/annotator.yaml` for EIS parameters, dataset paths, and UI colors.
