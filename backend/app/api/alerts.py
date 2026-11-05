"""Alerts API endpoints with SMS notification support."""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.app.database.repositories import AlertRepository
from backend.app.services.sms_service import send_alert_sms

logger = logging.getLogger(__name__)
router = APIRouter()


class AlertStatusUpdate(BaseModel):
    status: str  # ACKNOWLEDGED or RESOLVED


class ManualAlertCreate(BaseModel):
    """For testing — manually create an alert."""
    student_display_id: str = "ST-21CS101"
    student_name: Optional[str] = "Rahul Sharma"
    roll_number: Optional[str] = "21CS101"
    anomaly_score: float = 0.85
    phone_confidence: float = 0.92
    duration: float = 15.0
    context: str = "LECTURE"
    reasons: list = ["Phone detected near student for extended period"]


async def _send_sms_for_single_alert(alert_data: dict) -> list:
    """Send SMS to the specific student's mobile and their parent's mobile for an alert.

    Matches by roll_number or student_name in the student database.
    """
    sms_results = []
    try:
        student = None
        roll = alert_data.get("roll_number")
        name = alert_data.get("student_name")

        try:
            from backend.app.database.mongodb import get_db
            db = get_db()
            if db is not None:
                if roll and roll not in ("N/A", "Unknown", "UNKNOWN", ""):
                    student = await db.students.find_one({"roll_number": roll})
                if not student and name and name not in ("Unknown", "Unknown Person", "UNKNOWN", "Student", "Enrolled Student", ""):
                    student = await db.students.find_one({"name": name})
        except Exception as dbe:
            logger.debug(f"DB lookup skipped in SMS dispatch: {dbe}")

        # If student record found, use its details
        if student:
            stu_name = student.get("name", name or "Student")
            stu_roll = student.get("roll_number", roll or "N/A")
            student_mobile = student.get("mobile_number") or alert_data.get("student_mobile", "")
            parent_mobile = student.get("parent_mobile") or alert_data.get("parent_mobile", "")
            stu_info = {
                "name": stu_name,
                "roll_number": stu_roll,
                "department": student.get("department", alert_data.get("department", "")),
                "section": student.get("section", alert_data.get("section", "")),
            }
        else:
            stu_name = name or "Student"
            stu_roll = roll or alert_data.get("student_display_id", "N/A")
            student_mobile = alert_data.get("student_mobile", "")
            parent_mobile = alert_data.get("parent_mobile", "")
            stu_info = {
                "name": stu_name,
                "roll_number": stu_roll,
                "department": alert_data.get("department", "aiml"),
                "section": alert_data.get("section", "a"),
            }

        # Ensure evidence_url is present
        if not alert_data.get("evidence_url") and alert_data.get("evidence_path"):
            try:
                from backend.app.services.evidence_service import get_evidence_url
                alert_data["evidence_url"] = get_evidence_url(alert_data["evidence_path"])
            except Exception:
                pass

        # Send to student mobile
        if student_mobile:
            res_stu = await send_alert_sms(
                alert_data, student_mobile,
                student_info=stu_info, is_parent=False,
            )
            sms_results.append({
                "student": stu_name,
                "roll_number": stu_roll,
                "mobile": student_mobile,
                "type": "student",
                "message": res_stu.get("message", ""),
                "result": res_stu,
            })
            logger.info(f"SMS dispatched to Student {stu_name} ({student_mobile}): {res_stu.get('status')}")

        # Send to parent mobile
        if parent_mobile:
            res_parent = await send_alert_sms(
                alert_data, parent_mobile,
                student_info=stu_info, is_parent=True,
            )
            sms_results.append({
                "student": f"{stu_name} (parent)",
                "roll_number": stu_roll,
                "mobile": parent_mobile,
                "type": "parent",
                "message": res_parent.get("message", ""),
                "result": res_parent,
            })
            logger.info(f"SMS dispatched to Parent of {stu_name} ({parent_mobile}): {res_parent.get('status')}")

    except Exception as e:
        logger.error(f"Single alert SMS dispatch error: {e}")
        sms_results.append({"error": str(e)})

    return sms_results


async def _send_sms_to_students(alert_data: dict) -> list:
    """Send SMS for an alert.
    If alert is for a specific identified student (roll_number known), sends directly
    to that student's mobile and their parent's mobile.
    If alert belongs to an unidentified person (Unknown Person), skips SMS dispatch.
    """
    roll = alert_data.get("roll_number")
    name = alert_data.get("student_name")

    # If student is an unidentified unknown person, do NOT send SMS
    is_unknown = (
        not roll or 
        roll in ("UNKNOWN", "N/A", "Unknown", "") or 
        name in ("Unknown Person", "Unknown", "Enrolled Student")
    )
    if is_unknown and not (alert_data.get("student_mobile") or alert_data.get("parent_mobile")):
        logger.info(f"Skipping SMS: Alert {alert_data.get('alert_id')} is for an unidentified person (Unknown Person).")
        return []

    if roll and roll not in ("N/A", "Unknown", "UNKNOWN", ""):
        return await _send_sms_for_single_alert(alert_data)

    sms_results = []
    try:
        students = []
        try:
            from backend.app.database.mongodb import get_db
            db = get_db()
            if db is not None:
                students = await db.students.find({"is_active": True}).to_list(length=10)
        except Exception:
            pass

        for student in students:
            stu_info = {
                "name": student.get("name", ""),
                "roll_number": student.get("roll_number", ""),
                "department": student.get("department", ""),
                "section": student.get("section", ""),
                "semester": student.get("semester", ""),
            }

            # Send to student mobile
            mobile = student.get("mobile_number", "")
            if mobile:
                result = await send_alert_sms(
                    alert_data, mobile,
                    student_info=stu_info, is_parent=False,
                )
                sms_results.append({
                    "student": student.get("name", ""),
                    "roll_number": student.get("roll_number", ""),
                    "mobile": mobile,
                    "type": "student",
                    "result": result,
                })

            # Send to parent mobile
            parent_mobile = student.get("parent_mobile", "")
            if parent_mobile:
                result = await send_alert_sms(
                    alert_data, parent_mobile,
                    student_info=stu_info, is_parent=True,
                )
                sms_results.append({
                    "student": student.get("name", "") + " (parent)",
                    "roll_number": student.get("roll_number", ""),
                    "mobile": parent_mobile,
                    "type": "parent",
                    "result": result,
                })

    except Exception as e:
        logger.error(f"SMS notification error: {e}")
        sms_results.append({"error": str(e)})

    return sms_results


@router.get("/alerts")
async def get_alerts(status: Optional[str] = None, limit: int = 100, skip: int = 0):
    """Get all alerts, optionally filtered by status."""
    alerts = await AlertRepository.find_all(status=status, limit=limit, skip=skip)
    for a in alerts:
        a["_id"] = str(a["_id"])
    return {"alerts": alerts, "total": await AlertRepository.count(status)}


@router.get("/alerts/count")
async def alert_counts():
    """Get alert counts by status."""
    return {
        "total": await AlertRepository.count(),
        "new": await AlertRepository.count("NEW"),
        "acknowledged": await AlertRepository.count("ACKNOWLEDGED"),
        "resolved": await AlertRepository.count("RESOLVED"),
        "today": await AlertRepository.today_count(),
    }


@router.get("/alerts/{alert_id}")
async def get_alert(alert_id: str):
    """Get a specific alert by ID."""
    alert = await AlertRepository.find_by_id(alert_id)
    if not alert:
        raise HTTPException(404, "Alert not found")
    alert["_id"] = str(alert["_id"])
    return alert


@router.patch("/alerts/{alert_id}/status")
async def update_alert_status(alert_id: str, body: AlertStatusUpdate):
    """Update alert status (acknowledge or resolve)."""
    if body.status not in ("ACKNOWLEDGED", "RESOLVED"):
        raise HTTPException(400, "Status must be ACKNOWLEDGED or RESOLVED")
    success = await AlertRepository.update_status(alert_id, body.status)
    if not success:
        raise HTTPException(404, "Alert not found")
    return {"alert_id": alert_id, "status": body.status}


@router.post("/alerts/test")
async def create_test_alert(body: ManualAlertCreate):
    """Create a test alert and send SMS notifications.

    This endpoint is for testing the alert + SMS pipeline.
    In production, alerts are generated automatically by the AI pipeline.
    """
    import time
    import uuid

    alert_data = {
        "alert_id": str(uuid.uuid4())[:8].upper(),
        "student_tracking_id": 1,
        "student_display_id": body.student_display_id,
        "student_name": body.student_name or "Rahul Sharma",
        "roll_number": body.roll_number or "21CS101",
        "camera_id": "CAM-01",
        "event_type": "potential_unauthorized_phone_usage",
        "anomaly_score": body.anomaly_score,
        "phone_confidence": body.phone_confidence,
        "association_score": 0.0,
        "duration": body.duration,
        "timestamp": time.time(),
        "context": body.context,
        "reasons": body.reasons,
        "evidence_path": None,
        "evidence_url": None,
        "status": "NEW",
        "sms_sent": False,
    }

    # Save to MongoDB
    await AlertRepository.insert(alert_data)
    logger.info(f"Test alert created: {alert_data['alert_id']}")

    # Remove ObjectId before returning (not JSON-serializable)
    alert_data.pop("_id", None)

    # Send SMS to all enrolled students and parents
    sms_results = await _send_sms_to_students(alert_data)

    # Mark SMS as sent in DB if any were sent
    if any(r.get("result", {}).get("status") in ("sent", "logged") for r in sms_results if "result" in r):
        try:
            from backend.app.database.mongodb import get_db
            db = get_db()
            await db.alerts.update_one(
                {"alert_id": alert_data["alert_id"]},
                {"$set": {"sms_sent": True, "sms_count": len(sms_results)}},
            )
        except Exception:
            pass

    return {
        "alert": alert_data,
        "sms_notifications": sms_results,
        "message": f"Alert created. {len(sms_results)} SMS notification(s) processed.",
    }


@router.post("/alerts/{alert_id}/send-sms")
async def send_alert_notification(alert_id: str):
    """Send SMS notification for a specific existing alert."""
    alert = await AlertRepository.find_by_id(alert_id)
    if not alert:
        raise HTTPException(404, "Alert not found")

    # Convert _id for serialization
    alert.pop("_id", None)

    roll = alert.get("roll_number")
    name = alert.get("student_name")
    is_unknown = (
        not roll or 
        roll in ("UNKNOWN", "N/A", "Unknown", "") or 
        name in ("Unknown Person", "Unknown", "Enrolled Student")
    )
    if is_unknown and not (alert.get("student_mobile") or alert.get("parent_mobile")):
        return {
            "alert_id": alert_id,
            "sms_notifications": [],
            "count": 0,
            "message": "Cannot send SMS: Student is an unidentified person (Unknown Person). No mobile numbers linked.",
        }

    sms_results = await _send_sms_to_students(alert)

    # Mark SMS as sent and save dispatched logs in DB
    if any(r.get("result", {}).get("status") in ("sent", "logged") for r in sms_results if "result" in r):
        try:
            import time
            from backend.app.database.mongodb import get_db
            db = get_db()
            await db.alerts.update_one(
                {"alert_id": alert_id},
                {"$set": {
                    "sms_sent": True,
                    "sms_count": len(sms_results),
                    "sms_dispatched_at": time.time(),
                    "sms_notifications": sms_results,
                }},
            )
        except Exception as e:
            logger.error(f"Failed to record SMS sent status: {e}")

    return {
        "alert_id": alert_id,
        "sms_notifications": sms_results,
        "count": len(sms_results),
        "message": f"SMS sent successfully to {len(sms_results)} recipient(s) with student details and evidence clip link.",
    }


@router.delete("/alerts/{alert_id}")
async def delete_alert(alert_id: str):
    """Delete a specific alert."""
    from backend.app.database.mongodb import get_db
    db = get_db()
    result = await db.alerts.delete_one({"alert_id": alert_id})
    if result.deleted_count == 0:
        raise HTTPException(404, "Alert not found")
    return {"success": True, "message": f"Alert {alert_id} deleted"}
