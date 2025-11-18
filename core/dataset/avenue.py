import os

class AvenueAdapter:
    def __init__(self, annotation_file, videos_dir):
        """
        Avenue dataset adapter (frame-based).

        Args:
            annotation_file: Path to temporal annotation file
            videos_dir: Directory containing video files
        """
        self.annotation_file = annotation_file
        self.videos_dir = videos_dir
        self.videos = self._parse_annotations()

    def _parse_annotations(self):
        """Parse Avenue annotation file (frame-based)"""
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

                video_num = parts[0]  # e.g., "01"

                try:
                    start_frame = int(parts[1])
                    end_frame = int(parts[2])
                except (ValueError, IndexError):
                    continue

                # Use frame numbers directly (no FPS conversion!)
                if video_num not in video_intervals:
                    video_intervals[video_num] = []

                video_intervals[video_num].append((start_frame, end_frame))

        # Second pass: create video entries with intervals
        videos = []

        for video_num, intervals in video_intervals.items():
            # Video filename: {video_num}_video.mp4
            actual_video_name = f"{video_num}_video.mp4"

            # Check if video exists
            video_path = os.path.join(self.videos_dir, actual_video_name)
            if not os.path.exists(video_path):
                continue

            # Create separate entry for each interval
            for idx, interval in enumerate(intervals):
                start_frame, end_frame = interval
                display_name = f"{video_num} - Interval {idx + 1} [Frame {start_frame}-{end_frame}]"

                videos.append({
                    'name': actual_video_name,  # Actual filename
                    'display_name': display_name,
                    'annotation_name': video_num,  # Original annotation name
                    'interval_idx': idx,
                    'intervals': [interval]  # Single interval: (start_frame, end_frame)
                })

        return videos

    def get_videos(self):
        """Get list of videos"""
        return self.videos

    def expand_interval(self, start_frame, end_frame, expand_frames, max_frame=None):
        """
        Expand interval by expand_frames on both sides.

        Args:
            start_frame: Start frame number
            end_frame: End frame number
            expand_frames: Number of frames to expand on each side
            max_frame: Maximum frame number (video frame count - 1)

        Returns:
            tuple: (expanded_start, expanded_end)
        """
        start_expanded = max(0, start_frame - expand_frames)
        end_expanded = end_frame + expand_frames

        # Clamp to video frame count if provided
        if max_frame is not None:
            end_expanded = min(end_expanded, max_frame)

        return start_expanded, end_expanded
