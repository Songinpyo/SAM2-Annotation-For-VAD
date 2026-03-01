import os

import cv2


class VideoLoader:
    def __init__(self, media_path):
        self.media_path = media_path
        self.cap = None
        self.frame_paths = None
        self._frame_info = None

        if os.path.isdir(media_path):
            self.frame_paths = self._collect_frame_paths(media_path)
            if not self.frame_paths:
                raise ValueError(f"No readable frame images found: {media_path}")

            first_frame = self._read_frame_file(self.frame_paths[0])
            if first_frame is None:
                raise ValueError(f"Cannot read first frame image: {self.frame_paths[0]}")

            height, width = first_frame.shape[:2]
            self._frame_info = {
                'fps': 1.0,
                'width': width,
                'height': height,
                'frame_count': len(self.frame_paths),
            }
            return

        self.cap = cv2.VideoCapture(media_path)
        if not self.cap.isOpened():
            raise ValueError(f"Cannot open video: {media_path}")

    def _collect_frame_paths(self, frames_dir):
        image_exts = ('.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff', '.webp')
        frame_names = [
            name
            for name in os.listdir(frames_dir)
            if os.path.isfile(os.path.join(frames_dir, name)) and name.lower().endswith(image_exts)
        ]
        frame_names.sort()
        return [os.path.join(frames_dir, name) for name in frame_names]

    def _read_frame_file(self, frame_path):
        frame = cv2.imread(frame_path, cv2.IMREAD_UNCHANGED)
        if frame is None:
            return None

        if len(frame.shape) == 2:
            return cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)

        channels = frame.shape[2]
        if channels == 4:
            return cv2.cvtColor(frame, cv2.COLOR_BGRA2RGB)

        return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    def get_info(self):
        if self.frame_paths is not None:
            if self._frame_info is None:
                raise ValueError(f"Frame sequence is not initialized: {self.media_path}")
            return self._frame_info

        cap = self.cap
        if cap is None:
            raise ValueError(f"Video capture is not initialized: {self.media_path}")

        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        return {
            'fps': fps,
            'width': width,
            'height': height,
            'frame_count': frame_count,
        }

    def seek_to_second(self, second):
        """Seek to specific second and return frame (RGB) - DEPRECATED

        Use seek_to_frame() for the new frame-based system.
        """
        fps = self.get_info()['fps']
        frame_number = int(second * fps)
        return self.seek_to_frame(frame_number)

    def seek_to_frame(self, frame_number):
        """
        Seek to specific frame number and return frame (RGB).

        Args:
            frame_number (int): Frame number to seek to (0-indexed)

        Returns:
            numpy.ndarray: Frame in RGB format, or None if failed

        Example:
            >>> frame_rgb = loader.seek_to_frame(160)
        """
        if self.frame_paths is not None:
            if frame_number < 0 or frame_number >= len(self.frame_paths):
                return None
            return self._read_frame_file(self.frame_paths[frame_number])

        cap = self.cap
        if cap is None:
            return None

        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)

        ret, frame = cap.read()

        if not ret:
            return None

        # Convert BGR to RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        return frame_rgb

    def release(self):
        """Release video capture"""
        if self.cap is not None:
            self.cap.release()
