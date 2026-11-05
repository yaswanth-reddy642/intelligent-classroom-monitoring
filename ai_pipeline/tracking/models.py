"""Data models for multi-object tracking.

Privacy: This system uses anonymous tracking IDs only (ST-001, ST-002, etc.).
No facial identity recognition is performed.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Tuple
import time


class TrackState(str, Enum):
    """States for tracked objects."""
    ACTIVE = "active"
    LOST = "lost"
    REMOVED = "removed"
    POTENTIAL_PHONE_USE = "potential_phone_use"
    NORMAL = "normal"
    SUSPICIOUS = "suspicious"


@dataclass
class TrackedObject:
    """A tracked object with persistent anonymous identity across frames.

    Attributes:
        tracking_id: ByteTrack-assigned numeric ID.
        display_id: Anonymous display ID ('ST-001' or 'P-001').
        bbox: Bounding box (x1, y1, x2, y2) in pixels.
        confidence: Detection confidence.
        class_name: Object class ('student' or 'mobile_phone').
        first_seen: Timestamp when first detected.
        last_seen: Timestamp of most recent detection.
        state: Current tracking state.
    """
    tracking_id: int
    display_id: str
    bbox: Tuple[float, float, float, float]
    confidence: float
    class_name: str
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    state: TrackState = TrackState.ACTIVE
    student_name: Optional[str] = None
    roll_number: Optional[str] = None
    department: Optional[str] = None
    section: Optional[str] = None
    mobile_number: Optional[str] = None
    parent_mobile: Optional[str] = None
    match_confidence: float = 0.0
    identity_status: str = "Unverified"
    is_identified: bool = False
    is_unknown: bool = True
    consecutive_face_matches: int = 0
    is_concealed: bool = False

    @property
    def duration(self) -> float:
        """Duration in seconds since first detection."""
        return self.last_seen - self.first_seen

    @property
    def center(self) -> Tuple[float, float]:
        """Bounding box center point."""
        return ((self.bbox[0] + self.bbox[2]) / 2, (self.bbox[1] + self.bbox[3]) / 2)

    @property
    def width(self) -> float:
        """Bounding box width."""
        return self.bbox[2] - self.bbox[0]

    @property
    def height(self) -> float:
        """Bounding box height."""
        return self.bbox[3] - self.bbox[1]

    @property
    def label(self) -> str:
        """Display label with student identity if available."""
        if self.student_name and self.roll_number:
            return f"{self.student_name} ({self.roll_number})"
        return self.display_id

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "tracking_id": self.tracking_id,
            "display_id": self.display_id,
            "bbox": list(self.bbox),
            "confidence": round(self.confidence, 4),
            "class_name": self.class_name,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "duration": round(self.duration, 2),
            "state": self.state.value,
            "label": self.label,
            "student_name": self.student_name,
            "roll_number": self.roll_number,
            "department": getattr(self, "department", ""),
            "section": getattr(self, "section", ""),
            "mobile_number": self.mobile_number,
            "parent_mobile": self.parent_mobile,
            "match_confidence": getattr(self, "match_confidence", 0.0),
            "identity_status": getattr(self, "identity_status", "Unverified"),
            "is_identified": getattr(self, "is_identified", False),
            "is_unknown": getattr(self, "is_unknown", True),
            "is_concealed": getattr(self, "is_concealed", False),
        }
