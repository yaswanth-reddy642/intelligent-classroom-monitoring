"""FastAPI backend for Intelligent Classroom Monitoring.

Provides REST API endpoints, WebSocket live data streaming,
and MongoDB persistence for the AI pipeline.

Privacy: This system uses anonymous tracking IDs only (ST-XXX).
No facial identity recognition is performed.
"""

import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.app.core.config import get_settings
from backend.app.api import detection, alerts, students, statistics, settings, auth, analytics
from backend.app.websocket.manager import websocket_endpoint
from backend.app.services.inference_service import InferenceService
from backend.app.database.mongodb import connect_db, close_db

logger = logging.getLogger(__name__)

# Global inference service
inference_service: InferenceService = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    global inference_service
    app_settings = get_settings()

    # Connect to MongoDB
    await connect_db(app_settings.mongodb_uri, app_settings.mongodb_database)
    logger.info("MongoDB connected.")

    # Create default admin if needed
    from backend.app.api.auth import ensure_default_admin
    await ensure_default_admin()

    # Initialize inference service
    from ai_pipeline.config import load_config, setup_logging
    config = load_config()
    setup_logging(config.logging)
    inference_service = InferenceService(config)
    app.state.inference_service = inference_service

    # Register alert handler to persist pipeline alerts to MongoDB and broadcast
    import asyncio
    from backend.app.database.repositories import AlertRepository
    from backend.app.websocket.manager import broadcast_alert

    main_loop = asyncio.get_running_loop()

    async def _handle_pipeline_alert(alert_data: dict):
        try:
            # Ensure status and timestamp
            if "status" not in alert_data:
                alert_data["status"] = "NEW"

            from backend.app.database.mongodb import get_db
            db = get_db()

            # Ensure student details and contact numbers from DB if available
            roll = alert_data.get("roll_number")
            if db is not None and roll and roll not in ("N/A", "Unknown", "", "UNKNOWN"):
                stu = await db.students.find_one({"roll_number": roll})
                if stu:
                    alert_data["student_name"] = stu.get("name", alert_data.get("student_name"))
                    alert_data["department"] = stu.get("department", alert_data.get("department", ""))
                    alert_data["section"] = stu.get("section", alert_data.get("section", ""))
                    alert_data["student_mobile"] = stu.get("mobile_number", alert_data.get("student_mobile", ""))
                    alert_data["parent_mobile"] = stu.get("parent_mobile", alert_data.get("parent_mobile", ""))
            else:
                alert_data["student_name"] = alert_data.get("student_name") or "Unknown Person"
                if alert_data["student_name"] in ("Student", "Enrolled Student"):
                    alert_data["student_name"] = "Unknown Person"
                alert_data["roll_number"] = "UNKNOWN"
                alert_data["student_mobile"] = ""
                alert_data["parent_mobile"] = ""
                alert_data["department"] = "N/A"
                alert_data["section"] = "N/A"

            # Persist alert to MongoDB
            await AlertRepository.insert(alert_data)
            logger.info(f"Pipeline alert saved to MongoDB: {alert_data.get('alert_id')} for {alert_data.get('student_name')} ({alert_data.get('roll_number')})")

            # Broadcast alert to WebSocket clients
            await broadcast_alert(alert_data)

            # Auto-send SMS to student and parent mobile numbers
            from backend.app.api.alerts import _send_sms_for_single_alert
            sms_results = await _send_sms_for_single_alert(alert_data)
            if any(r.get("result", {}).get("status") in ("sent", "logged") for r in sms_results if "result" in r):
                if db is not None:
                    await db.alerts.update_one(
                        {"alert_id": alert_data["alert_id"]},
                        {"$set": {"sms_sent": True, "sms_count": len(sms_results)}},
                    )
                logger.info(f"Auto SMS notification sent for alert {alert_data.get('alert_id')} to student & parent ({len(sms_results)} messages).")
        except Exception as e:
            logger.error(f"Error persisting & notifying pipeline alert: {e}")

    def on_pipeline_alert(alert):
        alert_data = alert.to_dict() if hasattr(alert, "to_dict") else dict(alert)
        asyncio.run_coroutine_threadsafe(_handle_pipeline_alert(alert_data), main_loop)

    inference_service.register_alert_callback(on_pipeline_alert)
    logger.info("Inference service initialized and alert persistence callback registered.")

    yield

    # Shutdown
    inference_service.stop()
    await close_db()
    logger.info("Application shutdown complete.")


app = FastAPI(
    title="Intelligent Classroom Monitoring API",
    description="REST API for YOLOv11-based classroom monitoring with anonymous tracking",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for evidence images
evidence_path = os.path.join(os.path.dirname(__file__), "..", "..", "evidence")
os.makedirs(evidence_path, exist_ok=True)
app.mount("/evidence", StaticFiles(directory=evidence_path), name="evidence")

# API Routers
app.include_router(detection.router, prefix="/api", tags=["Detection"])
app.include_router(alerts.router, prefix="/api", tags=["Alerts"])
app.include_router(students.router, prefix="/api", tags=["Students"])
app.include_router(statistics.router, prefix="/api", tags=["Statistics"])
app.include_router(settings.router, prefix="/api", tags=["Settings"])
app.include_router(auth.router, prefix="/api", tags=["Auth"])
app.include_router(analytics.router, prefix="/api", tags=["Analytics"])

# Student photos static files
photos_path = os.path.join(os.path.dirname(__file__), "..", "..", "uploads", "photos")
os.makedirs(photos_path, exist_ok=True)
app.mount("/uploads/photos", StaticFiles(directory=photos_path), name="student_photos")

# WebSocket
app.add_api_websocket_route("/ws/live", websocket_endpoint)


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "classroom-monitoring-api",
        "version": "1.0.0",
    }
