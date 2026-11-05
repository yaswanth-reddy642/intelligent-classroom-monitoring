"""Data models for alerts."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List
import time
import uuid


class AlertStatus(str, Enum):
    NEW = "NEW"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"


@dataclass
class Alert:
    """Generated alert for potential unauthorized phone usage."""
    alert_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8].upper())
    student_tracking_id: int = 0
    student_display_id: str = ""
    student_name: Optional[str] = None
    roll_number: Optional[str] = None
    department: Optional[str] = None
    section: Optional[str] = None
    student_mobile: Optional[str] = None
    parent_mobile: Optional[str] = None
    camera_id: str = "CAM-01"
    event_type: str = "potential_unauthorized_phone_usage"
    anomaly_score: float = 0.0
    phone_confidence: float = 0.0
    association_score: float = 0.0
    duration: float = 0.0
    timestamp: float = field(default_factory=time.time)
    context: str = "LECTURE"
    reasons: List[str] = field(default_factory=list)
    evidence_path: Optional[str] = None
    evidence_url: Optional[str] = None
    status: AlertStatus = AlertStatus.NEW

    def to_dict(self) -> dict:
        return {
            "alert_id": self.alert_id,
            "student_tracking_id": self.student_tracking_id,
            "student_display_id": self.student_display_id,
            "student_name": self.student_name or "Unknown Person",
            "roll_number": self.roll_number or "UNKNOWN",
            "department": self.department or "",
            "section": self.section or "",
            "student_mobile": self.student_mobile or "",
            "parent_mobile": self.parent_mobile or "",
            "camera_id": self.camera_id,
            "event_type": self.event_type,
            "anomaly_score": round(self.anomaly_score, 4),
            "phone_confidence": round(self.phone_confidence, 4),
            "association_score": round(self.association_score, 4),
            "duration": round(self.duration, 2),
            "timestamp": self.timestamp,
            "context": self.context,
            "reasons": self.reasons,
            "evidence_path": self.evidence_path,
            "evidence_url": self.evidence_url,
            "status": self.status.value,
        }
