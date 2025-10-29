class UCFCrimeAdapter:
    def __init__(self, annotation_file, original_fps=30):
        self.annotation_file = annotation_file
        self.original_fps = original_fps
        self.videos = self._parse_annotations()

    def _parse_annotations(self):
        """Parse UCF-Crime annotation file"""
        videos = []

        with open(self.annotation_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                parts = line.split()
                if len(parts) < 3:
                    continue

                video_name = parts[0]
                # Add .mp4 extension if not present
                if not video_name.endswith('.mp4'):
                    video_name = video_name + '.mp4'

                anomaly_class = parts[1]

                # Parse intervals (format: start end start end ...)
                # Pairs of frame numbers, -1 means invalid
                intervals = []
                i = 2
                while i + 1 < len(parts):
                    try:
                        start_frame = int(parts[i])
                        end_frame = int(parts[i + 1])

                        # Skip invalid intervals (-1)
                        if start_frame < 0 or end_frame < 0:
                            i += 2
                            continue

                        # Convert frame numbers to seconds
                        start_sec = int(start_frame / self.original_fps)
                        end_sec = int(end_frame / self.original_fps)
                        intervals.append((start_sec, end_sec))
                    except (ValueError, IndexError):
                        # Skip invalid entries
                        pass

                    i += 2

                videos.append({
                    'name': video_name,
                    'class': anomaly_class,
                    'intervals': intervals
                })

        return videos

    def get_videos(self):
        """Get list of videos"""
        return self.videos

    def expand_interval(self, t0, t1, dt):
        """Expand interval by dt on both sides"""
        t0_prime = max(0, t0 - dt)
        t1_prime = t1 + dt
        return t0_prime, t1_prime
