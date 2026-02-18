# SAM2 Anomaly Annotation Tool

Annotation tool for anomaly detection datasets using Equal-Interval Seeding (EIS) strategy.

## Features

- Multi-entity annotation (actor, subject; legacy `related*` can be imported)
- Per-instance metadata support (text, enter frame, exit frame, missing frames)
- Multi-event metadata support (events[] with segment + perp/verb/subj/loca + assignments)
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
6. Author clip-level events in Event panel:
   - Use `Event` selector + `+/-` to manage multiple events per clip
   - For the first event, `Start/End` defaults to clip range start/end
   - Set event `Start/End` frames (spinner or `Use current`)
   - Fill `Perp/Verb/Subj/Loca` text
   - `Perp/Subj` supports comma-separated items; token order should follow checked entity order
     - actor order: `actor0 -> actor1 -> ... -> actor9`
     - subject order: `subject0 -> subject1 -> ... -> subject9`
   - `Loca` is copied by default when adding/removing events (editable after copy)
7. Navigate with A/D keys (frames) and T (next video)
8. Export when done (Ctrl+S or button)

Note: Export saves current video only. Repeat for each video.

### Keyboard Shortcuts

Frame navigation:
- A/D: Previous/Next frame
- T: Next video
- Ctrl+A/D: Previous/Next video
- F: Carry forward bbox

Entity selection:
- Q/W: Actor/Subject
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

- Event metadata (schema `2.1`):
  - `events[]` list (multiple events per clip)
  - `events[i].segment.start_frame`, `events[i].segment.end_frame`
  - `events[i].text.perp`, `events[i].text.verb`, `events[i].text.subj`, `events[i].text.loca`
  - `events[i].assignments.perp_entity_ids`, `events[i].assignments.subj_entity_ids`
  - Event ranges may overlap; each event remains an independent record
  - Authoring convention: if `perp` or `subj` has comma-separated tokens, token order must follow checked id order
    - actor order: `actor0 -> actor1 -> ... -> actor9`
    - subject order: `subject0 -> subject1 -> ... -> subject9`
  - Absence is valid: empty `perp/subj` text with empty assignment lists
- Per-instance appearance caption (`text`)
- Per-instance `enter_frame`, `exit_frame`, `missing_frames`
  - Stored as canonical `int[]` in JSON; UI may show compressed ranges for readability

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
  "schema_version": "2.1",
  "frame_indexing": "0-based",
  "events": [
    {
      "segment": {"start_frame": 60, "end_frame": 140},
      "text": {
        "perp": "man, man",
        "verb": "robbery",
        "subj": "woman, bag",
        "loca": "front yard"
      },
      "assignments": {
        "perp_entity_ids": ["actor0"],
        "subj_entity_ids": ["subject0", "subject1"]
      }
    },
    {
      "segment": {"start_frame": 180, "end_frame": 210},
      "text": {
        "perp": "man",
        "verb": "running",
        "subj": "",
        "loca": "alley"
      },
      "assignments": {
        "perp_entity_ids": [],
        "subj_entity_ids": []
      }
    }
  ],
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
- New export writes only schema `2.1` events metadata + per-instance metadata into `*.instances.json`

Reference examples in this repo:

- `annotations/ucf-crime2/Robbery102_x264_interval1.instances.json`
- `annotations/ucf-crime2/Robbery102_x264_interval1.txt`
- In this sample, `subj: "woman, bag"` aligns with `subj_entity_ids: ["subject0", "subject1"]`.

## Configuration

Edit `configs/annotator.yaml` for EIS parameters, dataset paths, and UI colors.
