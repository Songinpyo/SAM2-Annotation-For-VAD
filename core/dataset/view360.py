import os
import glob

class VIEW360Adapter:
    def __init__(self, annotation_file, videos_dir):
        """VIEW360 dataset adapter (frame-based)."""
        self.annotation_file = annotation_file
        self.videos_dir = videos_dir
        self.videos = self._parse_annotations()

    def _parse_annotations(self):
        """Parse VIEW360 annotation file (frame-based)"""
        # First pass: collect all intervals per video
        video_intervals = {}

        with open(self.annotation_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                parts = line.split()
                if len(parts) < 3:
                    continue

                video_name = parts[0]

                # Parse intervals (pairs: start end start end ...)
                if video_name not in video_intervals:
                    video_intervals[video_name] = []

                i = 1
                while i + 1 < len(parts):
                    try:
                        start_frame = int(parts[i])
                        end_frame = int(parts[i + 1])

                        # Use frame numbers directly (no FPS conversion!)
                        video_intervals[video_name].append((start_frame, end_frame))

                    except (ValueError, IndexError):
                        # Skip invalid entries
                        pass

                    i += 2

        # Second pass: create video entries with intervals
        videos = []

        for video_name, intervals in video_intervals.items():
            # Try multiple patterns to find video file
            actual_video_name = None

            # Pattern 1: {Location}_{video_name}_1fps.mp4
            video_pattern = os.path.join(self.videos_dir, f"*_{video_name}_1fps.mp4")
            matching_files = glob.glob(video_pattern)
            if matching_files:
                actual_video_name = os.path.basename(matching_files[0])

            # Pattern 2: {video_name}_1fps.mp4
            if not actual_video_name:
                alt_path = os.path.join(self.videos_dir, f"{video_name}_1fps.mp4")
                if os.path.exists(alt_path):
                    actual_video_name = f"{video_name}_1fps.mp4"

            # Pattern 3: {Location}_{video_name}.mp4
            if not actual_video_name:
                video_pattern = os.path.join(self.videos_dir, f"*_{video_name}.mp4")
                matching_files = glob.glob(video_pattern)
                if matching_files:
                    actual_video_name = os.path.basename(matching_files[0])

            # Pattern 4: {video_name}.mp4
            if not actual_video_name:
                alt_path = os.path.join(self.videos_dir, f"{video_name}.mp4")
                if os.path.exists(alt_path):
                    actual_video_name = f"{video_name}.mp4"

            # Skip if video file not found
            if not actual_video_name:
                continue

            # Create separate entry for each interval
            for idx, interval in enumerate(intervals):
                start_frame, end_frame = interval
                display_name = f"{video_name} - Interval {idx + 1} [Frame {start_frame}-{end_frame}]"

                videos.append({
                    'name': actual_video_name,  # Actual filename
                    'display_name': display_name,
                    'annotation_name': video_name,  # Original annotation name
                    'interval_idx': idx,
                    'intervals': [interval]  # Single interval: (start_frame, end_frame)
                })

        return videos

    def get_videos(self):
        """Get list of videos"""
        return self.videos

    def expand_interval(self, start_frame, end_frame, expand_frames, max_frame=None):
        """Expand interval by expand_frames on both sides"""
        start_expanded = max(0, start_frame - expand_frames)
        end_expanded = end_frame + expand_frames

        # Clamp to video frame count if provided
        if max_frame is not None:
            end_expanded = min(end_expanded, max_frame)

        return start_expanded, end_expanded
