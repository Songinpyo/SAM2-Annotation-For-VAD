import os


class MSADAdapter:
    """MSAD dataset adapter (frame-based, supports nested class folders)."""

    VIDEO_EXTS = ('.mp4', '.avi', '.mkv', '.mov')

    def __init__(self, annotation_file, videos_dir):
        self.annotation_file = annotation_file
        self.videos_dir = videos_dir
        self.videos = self._parse_annotations()

    def _index_videos(self):
        """
        Index all videos under videos_dir recursively.

        Returns:
            tuple[dict, dict, set]:
                - by_relative_noext: {"Class/VideoName": "Class/VideoName.mp4"}
                - by_basename_noext: {"VideoName": "Class/VideoName.mp4"} (None if ambiguous)
                - all_relative_with_ext: {"Class/VideoName.mp4", ...}
        """
        by_relative_noext = {}
        by_basename_noext = {}
        all_relative_with_ext = set()

        if not os.path.isdir(self.videos_dir):
            return by_relative_noext, by_basename_noext, all_relative_with_ext

        for root, _, files in os.walk(self.videos_dir):
            for filename in files:
                if not filename.lower().endswith(self.VIDEO_EXTS):
                    continue

                full_path = os.path.join(root, filename)
                rel_with_ext = os.path.relpath(full_path, self.videos_dir).replace(os.sep, '/')
                rel_noext = os.path.splitext(rel_with_ext)[0]
                base_noext = os.path.splitext(os.path.basename(rel_with_ext))[0]

                by_relative_noext[rel_noext] = rel_with_ext
                all_relative_with_ext.add(rel_with_ext)

                if base_noext not in by_basename_noext:
                    by_basename_noext[base_noext] = rel_with_ext
                elif by_basename_noext[base_noext] != rel_with_ext:
                    # Ambiguous basename across classes
                    by_basename_noext[base_noext] = None

        return by_relative_noext, by_basename_noext, all_relative_with_ext

    def _normalize_annotation_name(self, name):
        token = name.strip().replace('\\', '/')
        lowered = token.lower()
        for ext in self.VIDEO_EXTS:
            if lowered.endswith(ext):
                return token[: -len(ext)]
        return token

    def _resolve_video_name(self, annotation_name, by_relative_noext, by_basename_noext):
        if annotation_name in by_relative_noext:
            return by_relative_noext[annotation_name]

        base_name = os.path.basename(annotation_name)
        resolved = by_basename_noext.get(base_name)
        if resolved is not None:
            return resolved

        return None

    def _parse_annotations(self):
        videos = []
        self.missing_videos = []

        by_relative_noext, by_basename_noext, _ = self._index_videos()

        with open(self.annotation_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                parts = line.split()
                if len(parts) < 5:
                    continue

                annotation_name = self._normalize_annotation_name(parts[0])

                try:
                    total_frames = int(parts[1])
                    anomaly_flag = int(parts[2])
                    start_frame = int(parts[3])
                    end_frame = int(parts[4])
                except (ValueError, IndexError):
                    continue

                found_name = self._resolve_video_name(
                    annotation_name,
                    by_relative_noext,
                    by_basename_noext,
                )

                if not found_name:
                    self.missing_videos.append(annotation_name)
                    continue

                if anomaly_flag == 0:
                    display_name = f"{annotation_name} - Normal [Frame {start_frame}-{end_frame}]"
                else:
                    display_name = f"{annotation_name} - Anomaly [Frame {start_frame}-{end_frame}]"

                videos.append({
                    'name': found_name,
                    'display_name': display_name,
                    'annotation_name': annotation_name,
                    'interval_idx': 0,
                    'total_frames': total_frames,
                    'intervals': [(start_frame, end_frame)],
                })

        # Train/test split annotation files intentionally contain subsets while sharing
        # the same videos root, so "unannotated" would be mostly the opposite split.
        self.unannotated_videos = []
        return videos

    def get_videos(self):
        """Get list of videos."""
        return self.videos

    def expand_interval(self, start_frame, end_frame, expand_frames, max_frame=None):
        """Expand interval by expand_frames on both sides."""
        start_expanded = max(0, start_frame - expand_frames)
        end_expanded = end_frame + expand_frames

        if max_frame is not None:
            end_expanded = min(end_expanded, max_frame)

        return start_expanded, end_expanded
