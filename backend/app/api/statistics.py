"""Statistics API endpoints — dashboard data."""

import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Request

from backend.app.database.repositories import AlertRepository, StudentRepository

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/stats/dashboard")
async def dashboard_stats(request: Request):
    """Get dashboard summary statistics."""
    service = request.app.state.inference_service

    total_alerts = await AlertRepository.count()
    new_alerts = await AlertRepository.count("NEW")
    today_alerts = await AlertRepository.today_count()
    total_students = await StudentRepository.count()

    try:
        context = service.pipeline.context_engine.current_mode_str
    except Exception:
        context = "LECTURE"

    return {
        "pipeline_running": service.is_running,
        "fps": round(service.fps, 1),
        "total_alerts": total_alerts,
        "new_alerts": new_alerts,
        "today_alerts": today_alerts,
        "enrolled_students": total_students,
        "context": context,
    }


@router.get("/stats/live")
async def live_stats(request: Request):
    """Get real-time monitoring statistics."""
    service = request.app.state.inference_service
    state = service.get_current_state()

    return {
        "running": service.is_running,
        "fps": round(service.fps, 1),
        "frame_id": state.get("frame_id", 0),
        "student_count": state.get("student_count", 0),
        "phone_count": state.get("phone_count", 0),
        "active_tracks": len(state.get("tracks", [])),
        "context": service.pipeline.context_engine.current_mode_str,
        "new_alerts": service.pipeline.alert_engine.new_alert_count,
    }
