"""Video source abstraction for classroom monitoring.

Provides a unified interface for reading frames from video files,
webcams, and RTSP/IP camera streams. All sources share a common API
so the detection pipeline does not need to know the source type.
"""

import abc
import logging
import time
from typing import Optional, Tuple

import cv2
import numpy as np

from ai_pipeline.config import VideoConfig

logger = logging.getLogger(__name__)


class VideoSource(abc.ABC):
    """Abstract base class for all video sources."""

    def __init__(self, config: VideoConfig):
        self.config = config
        self._frame_count: int = 0
        self._start_time: float = 0.0
        self._is_opened: bool = False

    @property
    def source_type(self) -> str:
        return self.config.source_type

    @property
    def source_path(self) -> str:
        return self.config.source_path

    @abc.abstractmethod
    def start(self) -> bool:
        """Start the video source. Returns True on success."""

    @abc.abstractmethod
    def stop(self) -> None:
        """Stop and release the video source."""

    @abc.abstractmethod
    def read_frame(self) -> Optional[np.ndarray]:
        """Read the next frame. Returns None when no frame available."""

    @abc.abstractmethod
    def is_opened(self) -> bool:
        """Check if the video source is currently open."""

    @abc.abstractmethod
    def get_fps(self) -> float:
        """Get the frames per second of the source."""

    @abc.abstractmethod
    def get_resolution(self) -> Tuple[int, int]:
        """Get the native resolution (width, height)."""

    @abc.abstractmethod
    def get_frame_count(self) -> int:
        """Get total frame count (-1 for live sources)."""

    @abc.abstractmethod
    def get_current_position(self) -> int:
        """Get the current frame index."""


class FileVideoSource(VideoSource):
    """Video source for reading from MP4/AVI/MKV files."""

    def __init__(self, config: VideoConfig):
        super().__init__(config)
        self._cap: Optional[cv2.VideoCapture] = None
        self._total_frames: int = 0
        self._fps: float = 0.0

    def start(self) -> bool:
        try:
            path = self.source_path
            logger.info(f"Opening video file: {path}")

            self._cap = cv2.VideoCapture(path)
            if not self._cap.isOpened():
                logger.error(f"Failed to open video file: {path}")
                return False

            self._total_frames = int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self._fps = self._cap.get(cv2.CAP_PROP_FPS) or 30.0
            self._is_opened = True
            self._start_time = time.time()
            self._frame_count = 0
            w, h = self.get_resolution()
            logger.info(
                f"Video file opened: {path} "
                f"({w}x{h}, {self._fps:.1f} FPS, {self._total_frames} frames)"
            )
            return True
        except Exception as e:
            logger.error(f"Error opening video file '{self.source_path}': {e}")
            return False

    def stop(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        self._is_opened = False
        logger.info(f"Closed video file: {self.source_path}")

    def read_frame(self) -> Optional[np.ndarray]:
        if not self.is_opened() or self._cap is None:
            return None

        ret, frame = self._cap.read()
        if not ret or frame is None:
            # End of video file reached — automatically loop back to beginning
            try:
                self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self._cap.read()
                if ret and frame is not None:
                    logger.info(f"Video file looped back to beginning for continuous monitoring: {self.source_path}")
                else:
                    return None
            except Exception as e:
                logger.error(f"Error looping video file: {e}")
                return None

        # Normalize high resolution (e.g. 4K 3840x2160) to max 1280px width
        # This drastically speeds up CPU inference (from 400ms down to 60ms) and prevents lag
        h, w = frame.shape[:2]
        if w > 1280:
            scale = 1280.0 / w
            frame = cv2.resize(frame, (1280, int(h * scale)), interpolation=cv2.INTER_AREA)

        self._frame_count += 1
        return frame

    def is_opened(self) -> bool:
        return self._is_opened and self._cap is not None and self._cap.isOpened()

    def get_fps(self) -> float:
        return self._fps

    def get_resolution(self) -> Tuple[int, int]:
        if self._cap is not None:
            return (
                int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            )
        return (0, 0)

    def get_frame_count(self) -> int:
        return self._total_frames

    def get_current_position(self) -> int:
        return self._frame_count


class WebcamVideoSource(VideoSource):
    """Video source for reading from a local webcam."""

    def __init__(self, config: VideoConfig):
        super().__init__(config)
        self._cap: Optional[cv2.VideoCapture] = None
        self._fps: float = 0.0

    def start(self) -> bool:
        try:
            device_idx = int(self.source_path) if self.source_path.isdigit() else 0
            self._cap = cv2.VideoCapture(device_idx)

            if not self._cap.isOpened():
                logger.error(
                    f"Failed to open webcam (device {device_idx}). "
                    "Check that the camera is connected and not in use."
                )
                return False

            disp_res = self.config.display_resolution
            if disp_res and disp_res[0] > 0:
                self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, disp_res[0])
                self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, disp_res[1])

            if self.config.max_fps > 0:
                self._cap.set(cv2.CAP_PROP_FPS, self.config.max_fps)

            self._fps = self._cap.get(cv2.CAP_PROP_FPS) or 30.0
            self._is_opened = True
            self._start_time = time.time()
            self._frame_count = 0
            w, h = self.get_resolution()
            logger.info(f"Opened webcam (device {device_idx}): {w}x{h}, {self._fps:.1f} FPS")
            return True
        except Exception as e:
            logger.error(f"Error opening webcam '{self.source_path}': {e}")
            return False

    def stop(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        self._is_opened = False
        logger.info("Closed webcam")

    def read_frame(self) -> Optional[np.ndarray]:
        if not self.is_opened() or self._cap is None:
            return None

        ret, frame = self._cap.read()
        if not ret or frame is None:
            logger.warning("Failed to read frame from webcam.")
            return None

        self._frame_count += 1
        return frame

    def is_opened(self) -> bool:
        return self._is_opened and self._cap is not None and self._cap.isOpened()

    def get_fps(self) -> float:
        return self._fps

    def get_resolution(self) -> Tuple[int, int]:
        if self._cap is not None:
            return (
                int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            )
        return (0, 0)

    def get_frame_count(self) -> int:
        return -1

    def get_current_position(self) -> int:
        return self._frame_count


class RTSPVideoSource(VideoSource):
    """Video source for reading from RTSP/IP camera streams.

    Supports auto-reconnection on disconnect with configurable retries.
    Uses TCP transport for reliability over UDP.
    """

    def __init__(self, config: VideoConfig):
        super().__init__(config)
        self._cap: Optional[cv2.VideoCapture] = None
        self._fps: float = 0.0
        self._reconnect_attempts: int = 0
        self._max_reconnect_attempts: int = 10
        self._last_frame_time: float = 0.0

    def start(self) -> bool:
        return self._connect()

    def _connect(self) -> bool:
        import os
        import threading
        url = self.source_path
        logger.info(f"Connecting to RTSP stream: {url}")

        # If sample classroom stream requested, use local classroom recording
        is_virtual = False
        if any(k in url.lower() for k in ("classroom", "sample", "virtual", "testcam")):
            sample_candidates = [
                os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "uploads", "a1c9bebd_video.mp4")),
                os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "uploads", "0b118666_test_classroom.mp4")),
            ]
            for sc in sample_candidates:
                if os.path.exists(sc):
                    url = sc
                    is_virtual = True
                    logger.info(f"Using virtual classroom test stream from: {sc}")
                    break

        cap_holder = [None]
        opened = [False]

        def _open_stream():
            try:
                # Set TCP transport option for FFmpeg
                os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|stimeout;4000000"
                if is_virtual:
                    c = cv2.VideoCapture(url)
                else:
                    c = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
                    if not c.isOpened():
                        c.release()
                        c = cv2.VideoCapture(url)
                if c.isOpened():
                    cap_holder[0] = c
                    opened[0] = True
                else:
                    c.release()
            except Exception as e:
                logger.error(f"Error opening stream: {e}")

        # Connect with 5-second timeout to prevent blocking the server
        t = threading.Thread(target=_open_stream, daemon=True)
        t.start()
        t.join(timeout=5.0)

        if not opened[0] or cap_holder[0] is None:
            logger.error(f"Failed to open stream within 5s: {self.source_path}")
            return False

        self._cap = cap_holder[0]
        self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)
        fps = self._cap.get(cv2.CAP_PROP_FPS)
        self._fps = fps if (fps and 0 < fps <= 120) else 25.0
        self._is_opened = True
        self._reconnect_attempts = 0
        self._start_time = time.time()
        self._frame_count = 0
        w, h = self.get_resolution()
        logger.info(f"Connected to stream: {self.source_path} ({w}x{h}, {self._fps:.1f} FPS)")
        return True

    def stop(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        self._is_opened = False
        logger.info(f"Disconnected from RTSP stream: {self.source_path}")

    def read_frame(self) -> Optional[np.ndarray]:
        if not self.is_opened() or self._cap is None:
            return None

        ret, frame = self._cap.read()
        if not ret or frame is None:
            # If virtual stream, loop back to start
            if any(k in self.source_path.lower() for k in ("classroom", "sample", "virtual", "testcam")):
                try:
                    self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ret, frame = self._cap.read()
                except Exception:
                    pass
            if not ret or frame is None:
                logger.warning("Failed to read from RTSP stream.")
                self._handle_disconnect()
                return None

        # Normalize high resolution (e.g. 4K) to max 1280px width
        h, w = frame.shape[:2]
        if w > 1280:
            scale = 1280.0 / w
            frame = cv2.resize(frame, (1280, int(h * scale)), interpolation=cv2.INTER_AREA)

        self._frame_count += 1
        self._last_frame_time = time.time()
        return frame

    def _handle_disconnect(self) -> None:
        """Handle RTSP disconnection with auto-reconnect."""
        self._reconnect_attempts += 1
        if self._reconnect_attempts <= self._max_reconnect_attempts:
            wait = min(2 * self._reconnect_attempts, 10)  # Exponential backoff, max 10s
            logger.warning(
                f"RTSP stream disconnected. Reconnect attempt "
                f"{self._reconnect_attempts}/{self._max_reconnect_attempts} "
                f"in {wait}s..."
            )
            if self._cap is not None:
                self._cap.release()
                self._cap = None
            self._is_opened = False
            time.sleep(wait)
            self._connect()
        else:
            logger.error("Max RTSP reconnection attempts reached. Giving up.")
            self.stop()

    def is_opened(self) -> bool:
        return self._is_opened and self._cap is not None and self._cap.isOpened()

    def get_fps(self) -> float:
        return self._fps

    def get_resolution(self) -> Tuple[int, int]:
        if self._cap is not None:
            return (
                int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            )
        return (0, 0)

    def get_frame_count(self) -> int:
        return -1

    def get_current_position(self) -> int:
        return self._frame_count


def create_video_source(config: VideoConfig) -> VideoSource:
    """Factory function to create the appropriate VideoSource.

    Args:
        config: Video configuration specifying source type and parameters.

    Returns:
        A VideoSource instance matching the configured source type.

    Raises:
        ValueError: If source_type is not recognized.
    """
    source_type = config.source_type.lower()

    if source_type == "file":
        return FileVideoSource(config)
    elif source_type == "webcam":
        return WebcamVideoSource(config)
    elif source_type == "rtsp":
        return RTSPVideoSource(config)
    else:
        raise ValueError(
            f"Unsupported video source type: '{source_type}'. "
            "Use 'file', 'webcam', or 'rtsp'."
        )
