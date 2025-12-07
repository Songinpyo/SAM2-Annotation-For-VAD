import os

class UCFCrimeAdapter:
    def __init__(self, annotation_file):
        self.annotation_file = annotation_file
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

                        # Use frame numbers directly (no FPS conversion!)
                        intervals.append((start_frame, end_frame))
                    except (ValueError, IndexError):
                        # Skip invalid entries
                        pass

                    i += 2

                # Create separate video entry for each interval
                if not intervals:
                    continue

                for idx, interval in enumerate(intervals):
                    start_frame, end_frame = interval
                    display_name = f"{video_name} - Interval {idx + 1} [Frame {start_frame}-{end_frame}]"

                    videos.append({
                        'name': video_name,
                        'display_name': display_name,
                        'class': anomaly_class,
                        'interval_idx': idx,
                        'intervals': [interval]  # Single interval only
                    })

        # Second pass: check for content mismatches and track validation stats
        self.missing_videos = []
        
        # Get all actual video files in directory
        videos_dir = os.path.dirname(self.annotation_file.replace('annotations.txt', 'videos/'))
        if os.path.exists(videos_dir):
            all_files = set(os.listdir(videos_dir))
            actual_videos = {f for f in all_files if f.lower().endswith(('.mp4', '.avi', '.mkv', '.mov'))}
        else:
            actual_videos = set()
            
        matched_videos = set()

        valid_videos = []
        for v in videos:
            video_name = v['name']
            video_path = os.path.join(videos_dir, video_name)
            
            if os.path.exists(video_path):
                matched_videos.add(video_name)
                valid_videos.append(v)
            else:
                self.missing_videos.append(video_name)
        
        # Identify unannotated videos
        self.unannotated_videos = list(actual_videos - matched_videos)

        return valid_videos

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
