import os

class ShanghaiTechAdapter:
    def __init__(self, annotation_file, videos_dir, original_fps=25):
        self.annotation_file = annotation_file
        self.videos_dir = videos_dir
        self.original_fps = original_fps
        self.videos = self._parse_annotations()

    def _parse_annotations(self):
        """Parse ShanghaiTech annotation file

        Format: video_name total_frames anomaly_flag start_frame end_frame
        - anomaly_flag: 0 = normal (entire video), 1 = anomaly exists in [start, end]
        """
        videos = []

        with open(self.annotation_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                parts = line.split()
                if len(parts) < 5:
                    continue

                video_name = parts[0]
                try:
                    total_frames = int(parts[1])
                    anomaly_flag = int(parts[2])
                    start_frame = int(parts[3])
                    end_frame = int(parts[4])
                except (ValueError, IndexError):
                    continue

                # Video filename: {video_name}_video.mp4
                actual_video_name = f"{video_name}_video.mp4"

                # Check if video exists
                video_path = os.path.join(self.videos_dir, actual_video_name)
                if not os.path.exists(video_path):
                    continue

                # Convert frame numbers to seconds
                start_sec = int(start_frame / self.original_fps)
                end_sec = int(end_frame / self.original_fps)

                # Create video entry
                if anomaly_flag == 0:
                    # Normal video - use entire duration
                    display_name = f"{video_name} - Normal [{start_sec}-{end_sec}s]"
                else:
                    # Anomaly video - use specified interval
                    display_name = f"{video_name} - Anomaly [{start_sec}-{end_sec}s]"

                videos.append({
                    'name': actual_video_name,  # Actual filename
                    'display_name': display_name,
                    'annotation_name': video_name,  # Original annotation name
                    'interval_idx': 0,
                    'intervals': [(start_sec, end_sec)]
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
