# SAM2 Anomaly Annotation Tool

Annotation tool for anomaly detection datasets using Equal-Interval Seeding (EIS) strategy.

## Features

- Multi-entity annotation (actor, subject, related)
- Per-instance metadata support (text, enter frame, exit frame, missing frames)
- Optional video-level caption in sidecar JSON
- Undo/Redo history
- Import/Resume from existing annotations
- Validation on export

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python app/main.py
```

### Basic Workflow

1. Select dataset and video from left sidebar
2. Set run name (e.g., "v1" or "john_review")
3. Select entity (role + ID) and tool (bbox/pos_point/neg_point)
4. Draw annotations on frames
5. Set per-instance timeline metadata in the left panel:
   - Enter frame / Exit frame (or use current anchor)
   - Missing frames with list or ranges (e.g., `180-190,210`) or toggle current anchor
   - Bulk add/remove missing ranges with start/end controls
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

Annotations are saved as two files:

1) Prompt geometry TXT (`<video>.txt`)

- Relative coordinates in [0,1]
- Contains prompt rows only: `bbox`, `pos_point`, `neg_point`

2) Instance metadata sidecar JSON (`<video>.instances.json`)

- Optional video caption
- Per-instance text note
- Per-instance `enter_frame`, `exit_frame`, `missing_frames`

Prompt TXT example:

```
60, actor0, bbox, 0.512300, 0.338900, 0.080000, 0.210000
60, actor0, pos_point, 0.560000, 0.410000
70, actor0, bbox, 0.530000, 0.345000, 0.078000, 0.205000
```

Format: `frame, entity_id, type, coordinates...`

Instance metadata JSON example:

```json
{
  "schema_version": "1.0",
  "frame_indexing": "0-based",
  "video_caption": "Fight escalates near the center and disperses",
  "instances": {
    "actor0": {
      "text": "running away from explosion",
      "enter_frame": 60,
      "exit_frame": 140,
      "missing_frames": [95, 96]
    }
  }
}
```

Backward compatibility:

- Import still accepts legacy TXT rows with `frame=-1, type=text`
- New export writes text/temporal metadata into `*.instances.json`

## Configuration

Edit `configs/annotator.yaml` for EIS parameters, dataset paths, and UI colors.
