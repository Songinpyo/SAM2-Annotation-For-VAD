import os

class DOTAAdapter:
    def __init__(self, annotation_file, videos_dir, original_fps=30):
        self.annotation_file = annotation_file
        self.videos_dir = videos_dir
        self.original_fps = original_fps
        self.videos = self._parse_annotations()

    def _parse_annotations(self):
        """Parse DOTA annotation file"""
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

                video_name = parts[0]  # e.g., "0RJPQ_97dcs_000199"

                # Parse intervals - can have multiple intervals separated by commas
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

                            # Convert frame numbers to seconds
                            start_sec = int(start_frame / self.original_fps)
                            end_sec = int(end_frame / self.original_fps)

                            video_intervals[video_name].append((start_sec, end_sec))

                        except (ValueError, IndexError):
                            # Skip invalid entries
                            pass

        # Second pass: create video entries with intervals
        videos = []

        for video_name, intervals in video_intervals.items():
            # Video filename: {video_name}_video.mp4
            actual_video_name = f"{video_name}_video.mp4"

            # Check if video exists
            video_path = os.path.join(self.videos_dir, actual_video_name)
            if not os.path.exists(video_path):
                continue

            # Create separate entry for each interval
            for idx, interval in enumerate(intervals):
                t0, t1 = interval
                display_name = f"{video_name} - Interval {idx + 1} [{t0}-{t1}s]"

                videos.append({
                    'name': actual_video_name,  # Actual filename
                    'display_name': display_name,
                    'annotation_name': video_name,  # Original annotation name
                    'interval_idx': idx,
                    'intervals': [interval]  # Single interval only
                })

        return videos

    def get_videos(self):
        """Get list of videos"""
        return self.videos

    def expand_interval(self, t0, t1, dt, video_duration=None):
        """Expand interval by dt on both sides"""
        t0_prime = max(0, t0 - dt)
        t1_prime = t1 + dt

        # Clamp to video duration if provided
        if video_duration is not None:
            t1_prime = min(t1_prime, video_duration)

        return t0_prime, t1_prime
