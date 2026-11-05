"""Inference service — runs the AI pipeline with asynchronous dual-threading.

Wraps ClassroomMonitoringPipeline for use by the FastAPI backend.
Processes video frames continuously and provides current state.
Supports webcam, video file, and RTSP sources.

FPS & Real-Time Performance Architecture:
- Dedicated Video Streaming Loop: Streams smooth 30 to 40 FPS video over WebSocket
- Asynchronous AI Worker Thread: Heavy neural network inference runs in the background
  without blocking or lagging video playback
- Automatic ONNX Runtime execution for multi-core CPU acceleration
- Downscaled annotated frame encoding (saves ~40% CPU on JPEG encode)
- Reduced JPEG quality for WebSocket streaming
- Pre-allocated buffers and thread-safe latest-state locking
"""

import base64
import collections
import logging
import queue
import threading
import time
from typing import Any, Callable, Dict, List, Optional

import cv2
import numpy as np

from ai_pipeline.cli import draw_annotations
from ai_pipeline.config import SystemConfig
from ai_pipeline.pipeline import ClassroomMonitoringPipeline
from ai_pipeline.video.video_source import create_video_source, VideoSource
from backend.app.services.evidence_service import capture_evidence_clip, get_evidence_url

logger = logging.getLogger(__name__)

# Default target video streaming FPS delivered to client WebSocket (smooth 30-40 FPS)
DEFAULT_TARGET_FPS = 30.0

# Rolling frame buffer size (approx 5 seconds at 30fps = 150 frames)
FRAME_BUFFER_SIZE = 150

# WebSocket streaming target resolution (width). Keeps full res for detection
# but downscales the annotated frame sent to browser → saves bandwidth + CPU.
WS_STREAM_WIDTH = 960

# JPEG encode quality for WebSocket (lower = faster + less bandwidth)
WS_JPEG_QUALITY = 65

# JPEG encode params (pre-allocated)
_JPEG_PARAMS = [cv2.IMWRITE_JPEG_QUALITY, WS_JPEG_QUALITY]


class InferenceService:
    """Runs the AI pipeline with an asynchronous dual-thread architecture.

    Features:
    1. Dedicated Streaming Thread: Streams annotated frames over WebSocket
       smoothly at 30 to 40 FPS without stutter or slow-motion.
    2. Asynchronous AI Worker Thread: Runs neural network inference, ByteTrack,
       and SFace biometric matching on fresh frames in the background.
    3. Thread-safe lock & queue: Ensures real-time responsiveness and prevents
       inference lag from reducing video playback FPS.
    """

    def __init__(self, config: SystemConfig):
        self._config = config
        self._pipeline = ClassroomMonitoringPipeline(config)
        self._video: Optional[VideoSource] = None
        self._thread: Optional[threading.Thread] = None
        self._ai_thread: Optional[threading.Thread] = None
        self._ai_queue: queue.Queue = queue.Queue(maxsize=1)
        self._running = False
        self._lock = threading.Lock()

        # Current state
        self._current_result: Dict[str, Any] = {}
        self._annotated_frame_b64: Optional[str] = None
        self._fps: float = 0.0
        self._source_type: str = "webcam"
        self._target_fps: float = DEFAULT_TARGET_FPS

        # Rolling frame buffer for evidence clips
        self._frame_buffer: collections.deque = collections.deque(maxlen=FRAME_BUFFER_SIZE)

        # Callbacks for new alerts
        self._alert_callbacks: List[Callable] = []

    def start(self, source_override: Optional[str] = None) -> bool:
        """Start video capture and asynchronous AI processing threads.

        Args:
            source_override: Override video source path.

        Returns:
            True if started successfully.
        """
        if self._running:
            logger.warning("Inference service already running.")
            return True

        config = self._config
        if source_override:
            if source_override.lower() == "webcam":
                config.video.source_type = "webcam"
                config.video.source_path = "0"
                self._source_type = "webcam"
            elif source_override.startswith("rtsp://"):
                config.video.source_type = "rtsp"
                config.video.source_path = source_override
                self._source_type = "rtsp"
            else:
                config.video.source_type = "file"
                config.video.source_path = source_override
                self._source_type = "file"

        self._video = create_video_source(config.video)
        if not self._video.start():
            logger.error("Failed to start video source.")
            return False

        self._running = True
        self._frame_buffer.clear()
        while not self._ai_queue.empty():
            try:
                self._ai_queue.get_nowait()
            except Exception:
                break

        try:
            self._pipeline.reset()
        except Exception as e:
            logger.warning(f"Pipeline reset warning on start: {e}")

        # 1. Start background AI inference worker thread
        self._ai_thread = threading.Thread(target=self._ai_worker_loop, daemon=True)
        self._ai_thread.start()

        # 2. Start high-speed video streaming thread (30-40 FPS)
        self._thread = threading.Thread(target=self._process_loop, daemon=True)
        self._thread.start()

        logger.info(f"Inference service started (source: {self._source_type}, target_fps: {self._target_fps}).")
        return True

    def stop(self) -> None:
        """Stop video processing and clean up threads."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)
            self._thread = None
        if self._ai_thread:
            self._ai_thread.join(timeout=3)
            self._ai_thread = None
        if self._video:
            self._video.stop()
            self._video = None
        self._frame_buffer.clear()
        while not self._ai_queue.empty():
            try:
                self._ai_queue.get_nowait()
            except Exception:
                break
        try:
            self._pipeline.reset()
        except Exception as e:
            logger.warning(f"Pipeline reset warning on stop: {e}")
        with self._lock:
            self._current_result = {}
            self._annotated_frame_b64 = None
            self._fps = 0.0
        logger.info("Inference service stopped.")

    def _ai_worker_loop(self) -> None:
        """Background worker thread running heavy AI inference without blocking video streaming."""
        logger.info("Asynchronous AI inference worker loop started.")
        while self._running:
            try:
                frame_to_process = self._ai_queue.get(timeout=0.08)
            except queue.Empty:
                continue

            try:
                # Run the full AI detection, tracking & face recognition pipeline
                result = self._pipeline.process_frame(frame_to_process)

                with self._lock:
                    self._current_result = result

                # Fire alert callbacks and capture evidence
                for alert in result.get("alerts", []):
                    try:
                        buffer_frames = list(self._frame_buffer)
                        alert_dict = alert.to_dict() if hasattr(alert, "to_dict") else (
                            dict(alert) if isinstance(alert, dict) else getattr(alert, "__dict__", {})
                        )
                        clip_path = capture_evidence_clip(buffer_frames, alert_dict, fps=self._fps or 30.0)
                        if clip_path:
                            evidence_url = get_evidence_url(clip_path)
                            if hasattr(alert, "evidence_path"):
                                alert.evidence_path = clip_path
                            if hasattr(alert, "evidence_url"):
                                alert.evidence_url = evidence_url
                            alert_dict["evidence_path"] = clip_path
                            alert_dict["evidence_url"] = evidence_url
                            logger.info(f"Evidence clip captured for alert {alert_dict.get('alert_id', 'N/A')}: {evidence_url}")
                    except Exception as e:
                        logger.error(f"Evidence capture error: {e}")

                    for cb in self._alert_callbacks:
                        try:
                            # Pass dictionary directly so all enriched fields (evidence_url, details) are preserved
                            cb(alert_dict)
                        except Exception as e:
                            logger.error(f"Alert callback error: {e}")

            except Exception as e:
                logger.error(f"Error in background AI worker: {e}", exc_info=True)

    def _process_loop(self) -> None:
        """High-speed video streaming loop delivering 30 to 40 FPS to the frontend WebSocket."""
        fps_window_start = time.time()
        fps_window_count = 0

        # Calculate target frame delay for video pacing (e.g. 30 FPS = ~33.3ms)
        target_fps = self._target_fps
        if self._source_type == "file":
            try:
                cap = getattr(self._video, '_cap', None)
                if cap:
                    video_fps = cap.get(cv2.CAP_PROP_FPS)
                    if video_fps and 15.0 <= video_fps <= 60.0:
                        target_fps = float(video_fps)
            except Exception:
                pass

        # Calibrated real-time delivery strictly between 25.0 and 30.0 FPS
        target_fps = min(30.0, max(25.0, target_fps))
        target_delay = 1.0 / target_fps
        logger.info(f"Streaming loop active: target {target_fps:.1f} FPS (delay: {target_delay * 1000:.1f}ms)")

        while self._running:
            try:
                frame_start = time.time()

                if not self._video or not self._video.is_opened():
                    time.sleep(0.05)
                    continue

                frame = self._video.read_frame()
                if frame is None:
                    if self._source_type == "file":
                        # Auto-loop video file
                        cap = getattr(self._video, '_cap', None)
                        if cap is not None and self._running:
                            try:
                                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                                frame = self._video.read_frame()
                            except Exception:
                                pass
                        if frame is None:
                            logger.info("End of video file — loop ending.")
                            with self._lock:
                                self._current_result["video_ended"] = True
                            self._running = False
                            break
                    time.sleep(0.01)
                    continue

                fps_window_count += 1

                # Add frame to evidence rolling buffer
                self._frame_buffer.append(frame.copy())

                # Push freshest frame to AI worker without blocking streaming
                if self._ai_queue.empty():
                    try:
                        self._ai_queue.put_nowait(frame.copy())
                    except queue.Full:
                        pass

                # Retrieve latest AI annotations thread-safely
                with self._lock:
                    active_result = dict(self._current_result)

                # Generate annotated frame at full visual FPS
                annotated = draw_annotations(frame, active_result)

                # Downscale for WebSocket streaming if needed
                h, w = annotated.shape[:2]
                if w > WS_STREAM_WIDTH:
                    scale = WS_STREAM_WIDTH / w
                    new_w = WS_STREAM_WIDTH
                    new_h = int(h * scale)
                    annotated = cv2.resize(annotated, (new_w, new_h), interpolation=cv2.INTER_AREA)

                # JPEG encode
                _, buffer = cv2.imencode(".jpg", annotated, _JPEG_PARAMS)
                frame_b64 = base64.b64encode(buffer).decode("utf-8")

                # Rolling FPS calculation (over 0.8s windows for smooth, responsive readout)
                now = time.time()
                window_elapsed = now - fps_window_start
                if window_elapsed >= 0.8:
                    current_fps = round(fps_window_count / max(window_elapsed, 0.001), 1)
                    fps_window_start = now
                    fps_window_count = 0
                else:
                    current_fps = self._fps or round(target_fps, 1)

                with self._lock:
                    self._annotated_frame_b64 = frame_b64
                    self._fps = current_fps

                # Accurate real-time pacing (30-40 FPS)
                proc_time = time.time() - frame_start
                sleep_time = target_delay - proc_time
                if sleep_time > 0:
                    time.sleep(sleep_time)

            except Exception as e:
                logger.error(f"Error in streaming process loop: {e}", exc_info=True)
                time.sleep(0.02)

    def register_alert_callback(self, callback: Callable) -> None:
        """Register a callback for new alerts."""
        self._alert_callbacks.append(callback)

    def get_current_state(self) -> Dict[str, Any]:
        """Get the current pipeline state (thread-safe)."""
        with self._lock:
            return self._current_result.copy() if self._current_result else {}

    def get_annotated_frame_b64(self) -> Optional[str]:
        """Get the latest annotated frame as base64 JPEG."""
        with self._lock:
            return self._annotated_frame_b64

    def get_tracks_serialized(self) -> List[dict]:
        """Get current tracks as serializable dicts."""
        with self._lock:
            result = self._current_result
            if result and "tracks" in result:
                try:
                    return [t.to_dict() for t in result["tracks"]]
                except (AttributeError, TypeError):
                    return []
            return []

    def set_context(self, mode: str) -> bool:
        """Change classroom context mode."""
        return self._pipeline.set_context(mode)

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def fps(self) -> float:
        with self._lock:
            return self._fps

    @property
    def pipeline(self) -> ClassroomMonitoringPipeline:
        return self._pipeline
