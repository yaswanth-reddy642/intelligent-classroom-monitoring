"""Data models for temporal behavior analysis."""

from dataclasses import dataclass, field
from typing import Optional
import time


@dataclass
class TemporalRecord:
    """Single time-stamped observation for a student."""
    timestamp: float
    student_tracking_id: int
    phone_detected: bool = False
    phone_confidence: float = 0.0
    association_score: float = 0.0


@dataclass
class TemporalProfile:
    """Aggregated temporal behavior profile for a student.

    Computed from the sliding window of TemporalRecords.
    """
    student_tracking_id: int
    total_duration: float = 0.0           # Seconds with phone detected
    persistence_ratio: float = 0.0        # Fraction of window with phone
    consecutive_detections: int = 0       # Current consecutive phone frames
    max_consecutive: int = 0              # Max consecutive in window
    avg_phone_confidence: float = 0.0     # Average phone confidence when detected
    avg_association_score: float = 0.0    # Average association score when detected
    detection_consistency: float = 0.0    # How consistent detections are
    window_size: float = 0.0             # Current window duration in seconds

    def to_dict(self) -> dict:
        return {
            "student_tracking_id": self.student_tracking_id,
            "total_duration": round(self.total_duration, 2),
            "persistence_ratio": round(self.persistence_ratio, 4),
            "consecutive_detections": self.consecutive_detections,
            "max_consecutive": self.max_consecutive,
            "avg_phone_confidence": round(self.avg_phone_confidence, 4),
            "avg_association_score": round(self.avg_association_score, 4),
            "detection_consistency": round(self.detection_consistency, 4),
        }
