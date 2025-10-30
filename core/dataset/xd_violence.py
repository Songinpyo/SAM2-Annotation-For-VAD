class XDViolenceAdapter:
    def __init__(self, annotation_file, original_fps=30, gap_threshold=5):
        self.annotation_file = annotation_file
        self.original_fps = original_fps
        self.gap_threshold = gap_threshold
        self.videos = self._parse_annotations()

    def _parse_annotations(self):
        """Parse XD-Violence annotation file"""
        videos = []

        with open(self.annotation_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                parts = line.split()
                if len(parts) < 2:
                    continue

                video_name = parts[0]
                # Add .mp4 extension if not present
                if not video_name.endswith('.mp4'):
                    video_name = video_name + '.mp4'

                # Parse frame numbers
                frame_numbers = []
                for i in range(1, len(parts)):
                    if not parts[i]:  # Skip empty strings
                        continue
                    try:
                        frame_numbers.append(int(parts[i]))
                    except ValueError:
                        continue

                if not frame_numbers:
                    continue

                # Convert to intervals
                intervals = self._merge_frames_to_intervals(frame_numbers)

                # Create separate video entry for each interval
                if not intervals:
                    continue

                for idx, interval in enumerate(intervals):
                    t0, t1 = interval
                    display_name = f"{video_name} - Interval {idx + 1} [{t0}-{t1}s]"

                    videos.append({
                        'name': video_name,
                        'display_name': display_name,
                        'interval_idx': idx,
                        'intervals': [interval]  # Single interval only
                    })

        return videos

    def _merge_frames_to_intervals(self, frames):
        """Merge frame numbers into intervals"""
        if not frames:
            return []

        frames = sorted(frames)
        intervals = []
        start_frame = frames[0]
        end_frame = frames[0]

        for frame in frames[1:]:
            if frame - end_frame <= self.gap_threshold:
                end_frame = frame
            else:
                # Convert to seconds
                start_sec = int(start_frame / self.original_fps)
                end_sec = int(end_frame / self.original_fps)
                intervals.append((start_sec, end_sec))

                start_frame = frame
                end_frame = frame

        # Add last interval
        start_sec = int(start_frame / self.original_fps)
        end_sec = int(end_frame / self.original_fps)
        intervals.append((start_sec, end_sec))

        return intervals

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
