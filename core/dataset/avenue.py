import os

class AvenueAdapter:
    def __init__(self, annotation_file, videos_dir, original_fps=25):
        self.annotation_file = annotation_file
        self.videos_dir = videos_dir
        self.original_fps = original_fps
        self.videos = self._parse_annotations()

    def _parse_annotations(self):
        """Parse Avenue annotation file"""
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

                # Convert frame numbers to seconds
                start_sec = int(start_frame / self.original_fps)
                end_sec = int(end_frame / self.original_fps)

                if video_num not in video_intervals:
                    video_intervals[video_num] = []

                video_intervals[video_num].append((start_sec, end_sec))

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
                t0, t1 = interval
                display_name = f"{video_num} - Interval {idx + 1} [{t0}-{t1}s]"

                videos.append({
                    'name': actual_video_name,  # Actual filename
                    'display_name': display_name,
                    'annotation_name': video_num,  # Original annotation name
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
