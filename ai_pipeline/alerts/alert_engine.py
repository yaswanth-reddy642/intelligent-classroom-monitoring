"""Alert engine with per-student cooldown.

Generates alerts only when anomaly thresholds are met and
respects cooldown periods to prevent notification spam.
"""

import logging
import time
from typing import Dict, List, Callable, Optional

from ai_pipeline.config import AlertConfig
from ai_pipeline.alerts.models import Alert, AlertStatus
from ai_pipeline.anomaly.models import AnomalyResult, AnomalyClassification
from ai_pipeline.tracking.models import TrackedObject

logger = logging.getLogger(__name__)


class AlertEngine:
    """Generates and manages alerts with cooldown enforcement.

    Only creates an alert when:
    1. Anomaly score meets the POTENTIAL_ANOMALY threshold
    2. The student's cooldown period has expired
    3. The context does not suppress alerts
    """

    def __init__(self, config: AlertConfig, camera_id: str = "CAM-01"):
        self._config = config
        self._camera_id = camera_id
        self._cooldowns: Dict[int, float] = {}  # tracking_id -> last alert timestamp
        self._alerts: List[Alert] = []
        self._callbacks: List[Callable[[Alert], None]] = []

    def register_callback(self, callback: Callable[[Alert], None]) -> None:
        """Register a callback for new alerts (e.g. WebSocket, database)."""
        self._callbacks.append(callback)

    def get_last_alert_time(self, tracking_id: int) -> float:
        """Get the timestamp of the most recent alert for a student."""
        return self._cooldowns.get(tracking_id, 0.0)

    def check_and_alert(
        self,
        student: TrackedObject,
        anomaly: AnomalyResult,
        phone_confidence: float = 0.0,
        association_score: float = 0.0,
        consecutive_detections: int = 1,
        total_duration: float = 0.0,
        context_mode: str = "LECTURE",
        suppress: bool = False,
        evidence_path: Optional[str] = None,
    ) -> Optional[Alert]:
        """Check if an alert should be generated and create it if so.

        Args:
            student: The tracked student.
            anomaly: Anomaly scoring result.
            phone_confidence: Phone detection confidence.
            association_score: Association confidence.
            consecutive_detections: Sustained detections streak.
            total_duration: Total seconds phone observed with student.
            context_mode: Current classroom context.
            suppress: Whether alerts are suppressed by context.
            evidence_path: Path to evidence frame if captured.

        Returns:
            Alert if generated, None otherwise.
        """
        # Only alert on POTENTIAL_ANOMALY classification
        if anomaly.classification != AnomalyClassification.POTENTIAL_ANOMALY:
            return None

        # Check context suppression (e.g. BREAK, AUTHORIZED_PHONE_ACTIVITY)
        if suppress:
            return None

        # Temporal filter: require at least 3 consecutive frames or >= 1.2s duration
        # Prevents abnormal immediate alerts on single-frame noise or quick hand movements
        if consecutive_detections < 3 and total_duration < 1.2:
            return None

        # Confidence sanity filter: avoid alerting on low confidence detections
        # Lowered to 0.18 and 0.20 to reliably detect multiple handheld phones without missed alerts
        if phone_confidence < 0.18 or association_score < 0.20:
            return None

        # Check cooldown
        now = time.time()
        last_alert = self._cooldowns.get(student.tracking_id, 0)
        if now - last_alert < self._config.cooldown_seconds:
            return None

        # Create alert
        is_unknown = getattr(student, "is_unknown", False) or (getattr(student, "roll_number", None) in (None, "UNKNOWN", "N/A") or getattr(student, "student_name", None) in ("Unknown Person", "Unknown"))
        alert_name = "Unknown Person" if is_unknown else (getattr(student, "student_name", None) or "Unknown Person")
        alert_roll = "UNKNOWN" if is_unknown else (getattr(student, "roll_number", None) or "UNKNOWN")
        alert_stu_mob = "" if is_unknown else (getattr(student, "mobile_number", None) or "")
        alert_par_mob = "" if is_unknown else (getattr(student, "parent_mobile", None) or "")
        alert_dept = "" if is_unknown else (getattr(student, "department", None) or "")
        alert_sec = "" if is_unknown else (getattr(student, "section", None) or "")

        alert = Alert(
            student_tracking_id=student.tracking_id,
            student_display_id=student.display_id,
            student_name=alert_name,
            roll_number=alert_roll,
            department=alert_dept,
            section=alert_sec,
            student_mobile=alert_stu_mob,
            parent_mobile=alert_par_mob,
            camera_id=self._camera_id,
            anomaly_score=anomaly.score,
            phone_confidence=phone_confidence,
            association_score=association_score,
            duration=student.duration,
            context=context_mode,
            reasons=anomaly.reasons,
            evidence_path=evidence_path,
        )

        # Set cooldown
        self._cooldowns[student.tracking_id] = now
        self._alerts.append(alert)

        # Fire callbacks
        for cb in self._callbacks:
            try:
                cb(alert)
            except Exception as e:
                logger.error(f"Alert callback error: {e}")

        logger.warning(
            f"ALERT: {alert.event_type} | "
            f"Student: {student.label} | "
            f"Score: {alert.anomaly_score:.2f} | "
            f"Duration: {alert.duration:.1f}s | "
            f"Context: {context_mode}"
        )

        return alert

    def get_alerts(self, status: Optional[AlertStatus] = None) -> List[Alert]:
        """Get alerts, optionally filtered by status."""
        if status:
            return [a for a in self._alerts if a.status == status]
        return list(self._alerts)

    def acknowledge_alert(self, alert_id: str) -> bool:
        """Mark an alert as acknowledged."""
        for alert in self._alerts:
            if alert.alert_id == alert_id:
                alert.status = AlertStatus.ACKNOWLEDGED
                return True
        return False

    def resolve_alert(self, alert_id: str) -> bool:
        """Mark an alert as resolved."""
        for alert in self._alerts:
            if alert.alert_id == alert_id:
                alert.status = AlertStatus.RESOLVED
                return True
        return False

    @property
    def alert_count(self) -> int:
        return len(self._alerts)

    @property
    def new_alert_count(self) -> int:
        return len([a for a in self._alerts if a.status == AlertStatus.NEW])
