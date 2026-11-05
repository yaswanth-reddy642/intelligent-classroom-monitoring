"""Data models for face recognition."""

from dataclasses import dataclass, field
from typing import Optional, List, Tuple
import time
import numpy as np


@dataclass
class StudentProfile:
    """Enrolled student profile with face embeddings."""
    student_id: str                           # e.g., "STU-001"
    name: str                                 # e.g., "Rahul Sharma"
    roll_number: str                          # e.g., "21CS101"
    department: str = ""                      # e.g., "Computer Science"
    section: str = ""                         # e.g., "A"
    semester: int = 0
    face_embeddings: List[np.ndarray] = field(default_factory=list)
    photo_paths: List[str] = field(default_factory=list)
    enrolled_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    is_active: bool = True


@dataclass
class FaceDetectionResult:
    """Result of face detection within a student bounding box."""
    face_bbox: Tuple[float, float, float, float]  # (x1,y1,x2,y2) relative to full frame
    face_confidence: float
    student_bbox: Tuple[float, float, float, float]
    landmarks: Optional[np.ndarray] = None


@dataclass
class FaceEmbedding:
    """Face embedding vector."""
    embedding: np.ndarray  # 512-dim normalized vector
    quality_score: float = 0.0


@dataclass
class MatchResult:
    """Result of matching a face against the enrolled database."""
    matched: bool = False
    student_id: Optional[str] = None
    student_name: Optional[str] = None
    roll_number: Optional[str] = None
    department: Optional[str] = None
    section: Optional[str] = None
    similarity_score: float = 0.0


@dataclass
class EnrollmentResult:
    """Result of enrolling a student."""
    success: bool
    student_id: str = ""
    message: str = ""
    face_detected: bool = False
    embedding_extracted: bool = False
