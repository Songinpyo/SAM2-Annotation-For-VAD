import os

class ShanghaiTechAdapter:
    def __init__(self, annotation_file, videos_dir):
        """ShanghaiTech dataset adapter (frame-based)."""
        self.annotation_file = annotation_file
        self.videos_dir = videos_dir
        self.videos = self._parse_annotations()

    def _parse_annotations(self):
        """Parse ShanghaiTech annotation file (frame-based)

        Format: video_name total_frames anomaly_flag start_frame end_frame
        - anomaly_flag: 0 = normal (entire video), 1 = anomaly exists in [start, end]
        """
        videos = []
        self.missing_videos = []

        # Get all actual video files in directory
        if os.path.exists(self.videos_dir):
            all_files = set(os.listdir(self.videos_dir))
            actual_videos = {f for f in all_files if f.lower().endswith(('.mp4', '.avi', '.mkv', '.mov'))}
        else:
            actual_videos = set()
            
        matched_videos = set()

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

                except (ValueError, IndexError):
                    continue

                # Try patterns: "{name}_video.mp4" (old) and "{name}.mp4" (current)
                candidates = [f"{video_name}_video.mp4", f"{video_name}.mp4"]
                
                found_name = None
                for name in candidates:
                    if os.path.exists(os.path.join(self.videos_dir, name)):
                        found_name = name
                        break
                
                if not found_name:
                    self.missing_videos.append(video_name)
                    continue
                    
                matched_videos.add(found_name)

                # Use frame numbers directly (no FPS conversion!)
                # Create video entry
                if anomaly_flag == 0:
                    # Normal video - use entire duration
                    display_name = f"{video_name} - Normal [Frame {start_frame}-{end_frame}]"
                else:
                    # Anomaly video - use specified interval
                    display_name = f"{video_name} - Anomaly [Frame {start_frame}-{end_frame}]"

                videos.append({
                    'name': found_name,  # Actual filename
                    'display_name': display_name,
                    'annotation_name': video_name,  # Original annotation name
                    'interval_idx': 0,
                    'intervals': [(start_frame, end_frame)]
                })
        
        # Identify unannotated videos
        self.unannotated_videos = list(actual_videos - matched_videos)

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
