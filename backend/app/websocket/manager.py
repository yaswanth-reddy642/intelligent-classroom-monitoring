"""WebSocket manager for real-time live data streaming.

Streams annotated frames and detection data to connected
frontend clients at a configurable FPS.
"""

import asyncio
import json
import logging
from typing import Set

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

# Connected WebSocket clients
_active_connections: Set[WebSocket] = set()


async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for live monitoring feed.

    Streams JSON messages containing:
    - frame: base64-encoded JPEG of the annotated frame
    - tracks: list of currently tracked objects
    - stats: student/phone counts, FPS, context
    - alerts: any new alerts generated
    """
    await websocket.accept()
    _active_connections.add(websocket)
    logger.info(f"WebSocket client connected. Total: {len(_active_connections)}")

    try:
        service = websocket.app.state.inference_service

        while True:
            if not service.is_running:
                await websocket.send_json({"type": "status", "running": False})
                await asyncio.sleep(1)
                continue

            # Get current data
            frame_b64 = service.get_annotated_frame_b64()
            if frame_b64 is None:
                await asyncio.sleep(0.05)
                continue

            tracks = service.get_tracks_serialized()
            state = service.get_current_state()

            # Build message
            message = {
                "type": "frame",
                "frame": frame_b64,
                "tracks": tracks,
                "stats": {
                    "frame_id": state.get("frame_id", 0),
                    "student_count": state.get("student_count", 0),
                    "phone_count": state.get("phone_count", 0),
                    "fps": round(service.fps, 1),
                },
            }

            # Safely get context
            try:
                message["stats"]["context"] = service.pipeline.context_engine.current_mode_str
            except Exception:
                message["stats"]["context"] = "LECTURE"

            # Include anomalies
            if state and "anomalies" in state:
                message["anomalies"] = {
                    str(k): v.to_dict() for k, v in state["anomalies"].items()
                }

            await websocket.send_json(message)

            # Target 30-40 FPS for WebSocket streaming
            await asyncio.sleep(0.025)

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected.")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        _active_connections.discard(websocket)
        logger.info(f"WebSocket clients remaining: {len(_active_connections)}")


async def broadcast_alert(alert_data: dict):
    """Broadcast an alert to all connected WebSocket clients."""
    # Ensure all fields (e.g. MongoDB ObjectId) are JSON-serializable
    clean_alert = {k: str(v) if k == "_id" else v for k, v in alert_data.items()}
    message = json.dumps({"type": "alert", "alert": clean_alert})
    disconnected = set()
    for ws in _active_connections:
        try:
            await ws.send_text(message)
        except Exception:
            disconnected.add(ws)
    _active_connections.difference_update(disconnected)
