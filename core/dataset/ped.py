import os

class PedAdapter:
    def __init__(self, annotation_file, videos_dir):
        """Ped1/Ped2 dataset adapter (frame-based)."""
        self.annotation_file = annotation_file
        self.videos_dir = videos_dir
        self.videos = self._parse_annotations()

    def _parse_annotations(self):
        """Parse Ped1/Ped2 annotation file (frame-based)"""
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

                video_name = parts[0]  # e.g., "Test001"

                # Parse intervals - can have multiple intervals separated by commas
                # Example: Test005 5 90, 140 200
                interval_str = ' '.join(parts[1:])

                if video_name not in video_intervals:
                    video_intervals[video_name] = []

                # Split by comma to handle multiple intervals
                interval_groups = interval_str.split(',')

                for group in interval_groups:
                    group_parts = group.strip().split()
                    if len(group_parts) >= 2:
                        try:
                            start_frame = int(group_parts[0])
                            end_frame = int(group_parts[1])

                            # Use frame numbers directly (no FPS conversion!)
                            video_intervals[video_name].append((start_frame, end_frame))

                        except (ValueError, IndexError):
                            # Skip invalid entries
                            pass

        # Second pass: create video entries with intervals
        videos = []

        for video_name, intervals in video_intervals.items():
            # Convert Test001 -> 01_video.mp4
            # Extract numeric part from TestXXX
            if video_name.startswith('Test'):
                num_str = video_name.replace('Test', '').lstrip('0') or '0'
                try:
                    num = int(num_str)
                    actual_video_name = f"{num:02d}_video.mp4"
                except ValueError:
                    continue
            else:
                # Fallback: use as-is
                actual_video_name = f"{video_name}_video.mp4"

            # Check if video exists
            video_path = os.path.join(self.videos_dir, actual_video_name)
            if not os.path.exists(video_path):
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
