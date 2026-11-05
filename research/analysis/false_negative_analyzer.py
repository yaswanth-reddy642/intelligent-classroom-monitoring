"""False-negative analysis for anomaly detection.

Identifies missed anomalies and categorizes the failure mode.
"""

import logging
from dataclasses import dataclass
from typing import List, Dict, Optional
from collections import Counter

logger = logging.getLogger(__name__)


@dataclass
class FalseNegativeCase:
    """A single false-negative instance (missed anomaly)."""
    frame_id: int
    timestamp: float
    predicted_score: float
    category: str
    ground_truth_label: str
    phone_detected: bool
    association_score: float
    context: str
    notes: str = ""


FN_CATEGORIES = [
    "phone_not_detected",
    "association_missed",
    "temporal_too_short",
    "occlusion",
    "small_phone_missed",
    "crowded_scene",
    "tracking_id_switch",
    "low_model_confidence",
    "other",
]


class FalseNegativeAnalyzer:
    """Analyzes false negatives to understand missed anomalies."""

    def __init__(self):
        self._cases: List[FalseNegativeCase] = []

    def add_case(self, case: FalseNegativeCase) -> None:
        self._cases.append(case)

    def add_from_prediction(
        self,
        frame_id: int,
        timestamp: float,
        predicted_score: float,
        ground_truth: int,
        phone_detected: bool,
        association_score: float,
        context: str,
        phone_duration: float = 0.0,
        num_people: int = 0,
    ) -> Optional[FalseNegativeCase]:
        """Categorize a false negative (ground_truth=anomaly but predicted=normal)."""
        if ground_truth == 0:
            return None

        category = self._categorize(
            phone_detected, association_score, phone_duration,
            num_people, predicted_score,
        )

        case = FalseNegativeCase(
            frame_id=frame_id,
            timestamp=timestamp,
            predicted_score=predicted_score,
            category=category,
            ground_truth_label="anomaly",
            phone_detected=phone_detected,
            association_score=association_score,
            context=context,
        )
        self._cases.append(case)
        return case

    def _categorize(
        self,
        phone_detected: bool,
        association_score: float,
        phone_duration: float,
        num_people: int,
        score: float,
    ) -> str:
        if not phone_detected:
            return "phone_not_detected"
        if association_score < 0.1:
            return "association_missed"
        if phone_duration < 2.0:
            return "temporal_too_short"
        if num_people > 10:
            return "crowded_scene"
        if score < 0.3:
            return "low_model_confidence"
        return "other"

    def get_summary(self) -> Dict[str, any]:
        total = len(self._cases)
        category_counts = Counter(c.category for c in self._cases)
        return {
            "total_false_negatives": total,
            "by_category": dict(category_counts),
            "category_percentages": {
                k: round(v / total * 100, 1) if total > 0 else 0
                for k, v in category_counts.items()
            },
            "avg_predicted_score": round(
                sum(c.predicted_score for c in self._cases) / total, 4
            ) if total > 0 else 0,
        }

    def save_results(self, path: str) -> None:
        import csv, os
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "frame_id", "timestamp", "predicted_score", "category",
                "ground_truth_label", "phone_detected", "association_score",
                "context", "notes",
            ])
            writer.writeheader()
            for c in self._cases:
                writer.writerow({
                    "frame_id": c.frame_id, "timestamp": c.timestamp,
                    "predicted_score": c.predicted_score, "category": c.category,
                    "ground_truth_label": c.ground_truth_label,
                    "phone_detected": c.phone_detected,
                    "association_score": c.association_score,
                    "context": c.context, "notes": c.notes,
                })
        logger.info(f"Saved {len(self._cases)} false-negative cases to {path}")
