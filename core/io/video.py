import cv2
import numpy as np

class VideoLoader:
    def __init__(self, video_path):
        self.video_path = video_path
        self.cap = cv2.VideoCapture(video_path)

        if not self.cap.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")

    def get_info(self):
        """Get video information"""
        fps = self.cap.get(cv2.CAP_PROP_FPS)
        width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))

        return {
            'fps': fps,
            'width': width,
            'height': height,
            'frame_count': frame_count
        }

    def seek_to_second(self, second):
        """Seek to specific second and return frame (RGB)"""
        fps = self.cap.get(cv2.CAP_PROP_FPS)
        frame_number = int(second * fps)

        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)

        ret, frame = self.cap.read()

        if not ret:
            return None

        # Convert BGR to RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        return frame_rgb

    def release(self):
        """Release video capture"""
        if self.cap:
            self.cap.release()
