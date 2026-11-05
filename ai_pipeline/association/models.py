"""Data models for student-phone association."""

from dataclasses import dataclass, field
from typing import List, Optional
import time


@dataclass
class StudentPhoneAssociation:
    """Association between a tracked student and a detected phone.

    This represents a spatial and temporal link — NOT ownership proof.
    """
    student_tracking_id: int
    student_display_id: str
    phone_tracking_id: int
    phone_display_id: str
    association_score: float          # [0, 1] — spatial + temporal confidence
    spatial_score: float = 0.0       # Spatial proximity component
    containment_score: float = 0.0   # How much the phone is within the student bbox
    start_time: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    frame_count: int = 1             # Frames this association has persisted

    @property
    def duration(self) -> float:
        """Duration in seconds."""
        return self.last_seen - self.start_time

    def to_dict(self) -> dict:
        return {
            "student_display_id": self.student_display_id,
            "phone_display_id": self.phone_display_id,
            "association_score": round(self.association_score, 4),
            "spatial_score": round(self.spatial_score, 4),
            "containment_score": round(self.containment_score, 4),
            "duration": round(self.duration, 2),
            "frame_count": self.frame_count,
        }


@dataclass
class AssociationResult:
    """Frame-level association results."""
    associations: List[StudentPhoneAssociation] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    @property
    def count(self) -> int:
        return len(self.associations)
