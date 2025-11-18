class XDViolenceAdapter:
    def __init__(self, annotation_file, gap_threshold=5):
        self.annotation_file = annotation_file
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
                    start_frame, end_frame = interval
                    display_name = f"{video_name} - Interval {idx + 1} [Frame {start_frame}-{end_frame}]"

                    videos.append({
                        'name': video_name,
                        'display_name': display_name,
                        'interval_idx': idx,
                        'intervals': [interval]  # Single interval: (start_frame, end_frame)
                    })

        return videos

    def _merge_frames_to_intervals(self, frames):
        """Merge frame numbers into intervals (frame-based)"""
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
                # Use frame numbers directly (no FPS conversion!)
                intervals.append((start_frame, end_frame))

                start_frame = frame
                end_frame = frame

        # Add last interval
        intervals.append((start_frame, end_frame))

        return intervals

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
