import os


class AvenueAdapter:
    def __init__(self, annotation_file, videos_dir, frames_dir=None):
        self.annotation_file = annotation_file
        self.videos_dir = videos_dir
        self.frames_dir = frames_dir
        self.missing_videos = []
        self.unannotated_videos = []
        self.videos = self._parse_annotations()

    def _build_video_candidates(self, video_num):
        candidates = [f"{video_num}_video.mp4", f"{video_num}.mp4"]
        try:
            padded = f"{int(video_num):02d}"
        except ValueError:
            return candidates

        for candidate in (f"{padded}_video.mp4", f"{padded}.mp4"):
            if candidate not in candidates:
                candidates.append(candidate)

        return candidates

    def _build_frame_dir_candidates(self, video_num):
        candidates = [video_num]
        try:
            padded = f"{int(video_num):02d}"
        except ValueError:
            return candidates

        if padded not in candidates:
            candidates.append(padded)

        return candidates

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
        self.missing_videos = []

        # Get all actual video files in directory
        if os.path.exists(self.videos_dir):
            all_files = set(os.listdir(self.videos_dir))
            actual_videos = {f for f in all_files if f.lower().endswith(('.mp4', '.avi', '.mkv', '.mov'))}
        else:
            actual_videos = set()

        frames_dir = self.frames_dir
        if frames_dir and os.path.exists(frames_dir):
            all_entries = set(os.listdir(frames_dir))
            actual_frame_dirs = {
                name
                for name in all_entries
                if os.path.isdir(os.path.join(frames_dir, name))
            }
        else:
            actual_frame_dirs = set()

        matched_videos = set()
        matched_frame_dirs = set()

        for video_num, intervals in video_intervals.items():
            video_candidates = self._build_video_candidates(video_num)
            frame_candidates = self._build_frame_dir_candidates(video_num)

            media_type = None
            found_name = None
            media_path = None

            for dir_name in frame_candidates:
                if frames_dir is not None and dir_name in actual_frame_dirs:
                    media_type = 'frames'
                    found_name = dir_name
                    media_path = os.path.join(frames_dir, dir_name)
                    break

            if media_type is None:
                for file_name in video_candidates:
                    if file_name in actual_videos:
                        media_type = 'video'
                        found_name = file_name
                        media_path = os.path.join(self.videos_dir, file_name)
                        break

            if media_type is None or found_name is None or media_path is None:
                self.missing_videos.append(video_num)
                continue

            if media_type == 'frames':
                matched_frame_dirs.add(found_name)
                for candidate in video_candidates:
                    if candidate in actual_videos:
                        matched_videos.add(candidate)
            else:
                matched_videos.add(found_name)
                for candidate in frame_candidates:
                    if candidate in actual_frame_dirs:
                        matched_frame_dirs.add(candidate)

            # Create separate entry for each interval
            for idx, interval in enumerate(intervals):
                start_frame, end_frame = interval
                display_name = f"{video_num} - Interval {idx + 1} [Frame {start_frame}-{end_frame}]"

                videos.append({
                    'name': found_name,
                    'display_name': display_name,
                    'annotation_name': video_num,  # Original annotation name
                    'interval_idx': idx,
                    'intervals': [interval],  # Single interval: (start_frame, end_frame)
                    'media_type': media_type,
                    'media_path': media_path,
                })

        # Identify unannotated videos (files on disk but not in annotation)
        self.unannotated_videos = sorted((actual_videos - matched_videos) | (actual_frame_dirs - matched_frame_dirs))

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
