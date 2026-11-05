"""Evidence clip capture service — saves short video clips as evidence for alerts."""

import logging
import os
import time
import uuid
from datetime import datetime
from typing import List, Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)

EVIDENCE_BASE = os.path.join(os.path.dirname(__file__), "..", "..", "..", "evidence")
os.makedirs(EVIDENCE_BASE, exist_ok=True)


def capture_evidence_clip(
    frames: List[np.ndarray],
    alert_data: dict,
    fps: float = 15.0,
) -> str:
    """Save a short MP4 clip from a frame buffer as evidence.

    Args:
        frames: List of BGR frames (recent buffer).
        alert_data: Alert metadata for naming.
        fps: Frame rate for the output clip.

    Returns:
        Path to the saved evidence clip.
    """
    if not frames:
        return ""

    now = datetime.now()
    date_dir = os.path.join(EVIDENCE_BASE, now.strftime("%Y"), now.strftime("%m"), now.strftime("%d"))
    os.makedirs(date_dir, exist_ok=True)

    alert_id = alert_data.get("alert_id", uuid.uuid4().hex[:8])
    clip_name = f"alert_{alert_id}_{now.strftime('%H%M%S')}.mp4"
    clip_path = os.path.join(date_dir, clip_name)

    try:
        h, w = frames[0].shape[:2]
        # H.264 requires dimensions divisible by 2
        w = w - (w % 2)
        h = h - (h % 2)

        encoded = False
        try:
            import av
            container = av.open(clip_path, mode="w", format="mp4", options={"movflags": "faststart"})
            stream = container.add_stream("libx264", rate=max(1, int(round(fps))))
            stream.width = w
            stream.height = h
            stream.pix_fmt = "yuv420p"
            stream.options = {"preset": "veryfast", "crf": "23"}

            for frame in frames:
                if frame.shape[1] != w or frame.shape[0] != h:
                    frame = cv2.resize(frame, (w, h))
                av_frame = av.VideoFrame.from_ndarray(frame, format="bgr24")
                for packet in stream.encode(av_frame):
                    container.mux(packet)

            for packet in stream.encode():
                container.mux(packet)
            container.close()
            encoded = True
            logger.info(f"Evidence clip encoded using native H.264 libx264 ({len(frames)} frames)")
        except Exception as av_err:
            logger.warning(f"PyAV H.264 encoder error, falling back to cv2: {av_err}")

        if not encoded:
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(clip_path, fourcc, fps, (w, h))
            for frame in frames:
                if frame.shape[1] != w or frame.shape[0] != h:
                    frame = cv2.resize(frame, (w, h))
                writer.write(frame)
            writer.release()

        size_kb = os.path.getsize(clip_path) / 1024
        logger.info(f"Evidence clip saved: {clip_path} ({len(frames)} frames, {size_kb:.1f}KB)")
        return clip_path
    except Exception as e:
        logger.error(f"Failed to save evidence clip: {e}")
        return ""


def get_evidence_url(clip_path: str) -> str:
    """Convert absolute clip path to a URL-safe relative path."""
    if not clip_path:
        return ""
    try:
        rel = os.path.relpath(clip_path, EVIDENCE_BASE)
        return f"/evidence/{rel.replace(os.sep, '/')}"
    except Exception:
        return ""
