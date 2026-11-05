"""Data models for classroom context."""

from dataclasses import dataclass
from enum import Enum


class ContextMode(str, Enum):
    """Classroom operating modes."""
    LECTURE = "LECTURE"
    EXAM = "EXAM"
    AUTHORIZED_PHONE_ACTIVITY = "AUTHORIZED_PHONE_ACTIVITY"
    BREAK = "BREAK"


@dataclass
class ClassroomContext:
    """Current classroom context state."""
    mode: ContextMode = ContextMode.LECTURE
    multiplier: float = 1.0
    suppress_alerts: bool = False
