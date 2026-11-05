"""Detection API endpoints — start/stop inference, upload video, get detections."""

import logging
import os
import uuid
from typing import Optional

from fastapi import APIRouter, Request, HTTPException, UploadFile, File
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()

# Directory for uploaded video files
UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "uploads"))
os.makedirs(UPLOAD_DIR, exist_ok=True)


class StartRequest(BaseModel):
    source: Optional[str] = None


@router.post("/detection/upload-video")
async def upload_video(file: UploadFile = File(...)):
    """Upload a video file for processing.

    Returns the server-side path to use with /detection/start.
    Accepts .mp4, .avi, .mkv, .mov, .wmv formats.
    """
    allowed_ext = {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".webm"}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_ext:
        raise HTTPException(400, f"Unsupported format: {ext}. Use: {', '.join(allowed_ext)}")

    # Save with unique name to avoid collisions
    safe_name = f"{uuid.uuid4().hex[:8]}_{file.filename}"
    save_path = os.path.normpath(os.path.join(UPLOAD_DIR, safe_name))

    try:
        content = await file.read()
        with open(save_path, "wb") as f:
            f.write(content)
        logger.info(f"Video uploaded: {save_path} ({len(content)} bytes)")
        return {
            "filename": file.filename,
            "path": save_path,
            "size_mb": round(len(content) / (1024 * 1024), 2),
        }
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(500, f"Upload failed: {e}")


@router.post("/detection/start")
async def start_detection(request: Request, body: StartRequest = StartRequest()):
    """Start the inference pipeline.

    Source can be:
    - 'webcam' or None: Use default webcam
    - A file path: Use uploaded or local video file
    - 'rtsp://...': Use RTSP stream

    If already running, stops the current session first.
    """
    service = request.app.state.inference_service
    if service.is_running:
        logger.info("Detection already running — stopping before restart.")
        service.stop()

    source = body.source or "webcam"
    logger.info(f"Starting detection with source: {source}")

    # Handle classroom sample aliases
    if any(k in source.lower() for k in ("classroom_sample", "sample://classroom", "virtual://classroom", "sample_classroom")):
        sample_path = os.path.normpath(os.path.join(UPLOAD_DIR, "a1c9bebd_video.mp4"))
        if not os.path.exists(sample_path):
            mp4s = [f for f in os.listdir(UPLOAD_DIR) if f.endswith(".mp4")]
            if mp4s:
                sample_path = os.path.normpath(os.path.join(UPLOAD_DIR, mp4s[0]))
        source = sample_path
        logger.info(f"Resolved classroom test stream to: {source}")

    # Resolve relative filename or filename in UPLOAD_DIR
    if not os.path.isabs(source) and not source.startswith("rtsp://") and not source.startswith("http://") and source != "webcam":
        candidate = os.path.normpath(os.path.join(UPLOAD_DIR, source))
        if os.path.exists(candidate):
            source = candidate

    success = service.start(source)
    if not success:
        if source.startswith("rtsp://") or source.startswith("http://"):
            raise HTTPException(400, f"Failed to connect to stream '{source}'. Stream timed out or is offline.")
        raise HTTPException(500, f"Failed to start video source: '{source}'. Check file path or camera connection.")
    return {"status": "started", "source": source}


@router.post("/detection/stop")
async def stop_detection(request: Request):
    """Stop the inference pipeline."""
    service = request.app.state.inference_service
    service.stop()
    return {"status": "stopped"}


@router.get("/detection/status")
async def detection_status(request: Request):
    """Get inference pipeline status."""
    service = request.app.state.inference_service
    return {
        "running": service.is_running,
        "fps": round(service.fps, 1),
    }


@router.get("/detection/current")
async def current_detections(request: Request):
    """Get current frame detections and tracks."""
    service = request.app.state.inference_service
    if not service.is_running:
        return {"running": False, "tracks": [], "detections": None}

    tracks = service.get_tracks_serialized()
    state = service.get_current_state()

    detections = None
    if state and "detections" in state and state["detections"]:
        detections = state["detections"].to_dict()

    anomalies = {}
    if state and "anomalies" in state:
        anomalies = {str(k): v.to_dict() for k, v in state["anomalies"].items()}

    return {
        "running": True,
        "frame_id": state.get("frame_id", 0),
        "tracks": tracks,
        "detections": detections,
        "anomalies": anomalies,
        "student_count": state.get("student_count", 0),
        "phone_count": state.get("phone_count", 0),
    }


@router.get("/detection/frame")
async def get_annotated_frame(request: Request):
    """Get the latest annotated frame as base64 JPEG."""
    service = request.app.state.inference_service
    frame = service.get_annotated_frame_b64()
    if not frame:
        raise HTTPException(404, "No frame available.")
    return {"frame": frame}
