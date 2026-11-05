"""Data models for anomaly scoring."""

from dataclasses import dataclass, field
from enum import Enum
from typing import List


class AnomalyClassification(str, Enum):
    """Anomaly classification levels.

    Does NOT claim 'confirmed violation' — uses probabilistic language.
    """
    NORMAL = "NORMAL"
    SUSPICIOUS = "SUSPICIOUS"
    POTENTIAL_ANOMALY = "POTENTIAL_ANOMALY"


@dataclass
class AnomalyResult:
    """Result of anomaly scoring for a student.

    Attributes:
        score: Normalized anomaly score in [0, 1].
        classification: Classification level.
        reasons: Human-readable reasons for the score.
        components: Individual score components for transparency.
    """
    score: float = 0.0
    classification: AnomalyClassification = AnomalyClassification.NORMAL
    reasons: List[str] = field(default_factory=list)
    components: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "anomaly_score": round(self.score, 4),
            "classification": self.classification.value,
            "reasons": self.reasons,
            "components": {k: round(v, 4) for k, v in self.components.items()},
        }
