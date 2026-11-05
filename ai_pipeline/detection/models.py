"""Data models for object detection results."""

from dataclasses import dataclass, field
from typing import List, Tuple
import time


@dataclass
class Detection:
    """Single object detection result.

    Attributes:
        bbox: Bounding box as (x1, y1, x2, y2) in pixels.
        class_id: Model output class ID.
        class_name: Mapped project class name (e.g. 'student', 'mobile_phone').
        confidence: Detection confidence score in [0, 1].
        original_class_name: Original model class name (e.g. 'person').
    """
    bbox: Tuple[float, float, float, float]
    class_id: int
    class_name: str
    confidence: float
    original_class_name: str = ""

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
    def area(self) -> float:
        """Bounding box area in pixels."""
        return max(0, self.width) * max(0, self.height)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "bbox": list(self.bbox),
            "class_id": self.class_id,
            "class_name": self.class_name,
            "confidence": round(self.confidence, 4),
            "original_class_name": self.original_class_name,
            "center": list(self.center),
        }


@dataclass
class DetectionResult:
    """Frame-level detection result containing all detections.

    Attributes:
        frame_id: Frame sequence number.
        timestamp: Time of detection.
        detections: List of all detections in this frame.
        inference_time_ms: Model inference time in milliseconds.
    """
    frame_id: int
    timestamp: float = field(default_factory=time.time)
    detections: List[Detection] = field(default_factory=list)
    inference_time_ms: float = 0.0

    @property
    def students(self) -> List[Detection]:
        """Get all student detections."""
        return [d for d in self.detections if d.class_name == "student"]

    @property
    def phones(self) -> List[Detection]:
        """Get all mobile phone detections."""
        return [d for d in self.detections if d.class_name == "mobile_phone"]

    @property
    def student_count(self) -> int:
        """Number of students detected."""
        return len(self.students)

    @property
    def phone_count(self) -> int:
        """Number of phones detected."""
        return len(self.phones)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "frame_id": self.frame_id,
            "timestamp": self.timestamp,
            "student_count": self.student_count,
            "phone_count": self.phone_count,
            "inference_time_ms": round(self.inference_time_ms, 2),
            "detections": [d.to_dict() for d in self.detections],
        }
