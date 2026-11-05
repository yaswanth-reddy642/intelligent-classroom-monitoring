"""False-positive analysis for anomaly detection.

Categorizes false positives by cause to identify systematic errors.
"""

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from collections import Counter

logger = logging.getLogger(__name__)


@dataclass
class FalsePositiveCase:
    """A single false-positive instance."""
    frame_id: int
    timestamp: float
    predicted_score: float
    category: str  # Category of the false positive
    student_id: str
    phone_detected: bool
    association_score: float
    context: str
    notes: str = ""


FP_CATEGORIES = [
    "short_phone_detection",
    "incorrect_association",
    "occlusion",
    "small_phone",
    "tracking_loss",
    "authorized_phone_activity",
    "break_period",
    "low_confidence_detection",
    "context_misconfiguration",
    "other",
]


class FalsePositiveAnalyzer:
    """Analyzes false-positive alerts to identify systematic failure patterns."""

    def __init__(self):
        self._cases: List[FalsePositiveCase] = []

    def add_case(self, case: FalsePositiveCase) -> None:
        """Add a false-positive case."""
        self._cases.append(case)

    def add_from_prediction(
        self,
        frame_id: int,
        timestamp: float,
        predicted_score: float,
        ground_truth: int,
        student_id: str,
        phone_detected: bool,
        association_score: float,
        context: str,
        phone_duration: float = 0.0,
        phone_size: float = 0.0,
        track_age: float = 0.0,
    ) -> Optional[FalsePositiveCase]:
        """Automatically categorize a false positive based on features.

        Only processes cases where predicted=anomaly but ground_truth=normal.
        """
        if ground_truth == 1:  # True positive, not a false positive
            return None

        # Categorize based on features
        category = self._categorize(
            phone_detected, association_score, context,
            phone_duration, phone_size, track_age, predicted_score,
        )

        case = FalsePositiveCase(
            frame_id=frame_id,
            timestamp=timestamp,
            predicted_score=predicted_score,
            category=category,
            student_id=student_id,
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
        context: str,
        phone_duration: float,
        phone_size: float,
        track_age: float,
        score: float,
    ) -> str:
        """Heuristic categorization of false-positive cause."""
        if context in ("AUTHORIZED_PHONE_ACTIVITY", "BREAK"):
            if context == "AUTHORIZED_PHONE_ACTIVITY":
                return "authorized_phone_activity"
            return "break_period"

        if phone_duration < 2.0:
            return "short_phone_detection"

        if phone_size < 20:
            return "small_phone"

        if association_score < 0.3 and phone_detected:
            return "incorrect_association"

        if track_age < 1.0:
            return "tracking_loss"

        if score < 0.5:
            return "low_confidence_detection"

        return "other"

    def get_summary(self) -> Dict[str, any]:
        """Generate summary statistics."""
        category_counts = Counter(c.category for c in self._cases)
        total = len(self._cases)

        return {
            "total_false_positives": total,
            "by_category": dict(category_counts),
            "category_percentages": {
                k: round(v / total * 100, 1) if total > 0 else 0
                for k, v in category_counts.items()
            },
            "avg_score": round(
                sum(c.predicted_score for c in self._cases) / total, 4
            ) if total > 0 else 0,
            "contexts": dict(Counter(c.context for c in self._cases)),
        }

    def save_results(self, path: str) -> None:
        """Save analysis results to CSV."""
        import csv
        import os
        os.makedirs(os.path.dirname(path), exist_ok=True)

        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "frame_id", "timestamp", "predicted_score", "category",
                "student_id", "phone_detected", "association_score",
                "context", "notes",
            ])
            writer.writeheader()
            for case in self._cases:
                writer.writerow({
                    "frame_id": case.frame_id,
                    "timestamp": case.timestamp,
                    "predicted_score": case.predicted_score,
                    "category": case.category,
                    "student_id": case.student_id,
                    "phone_detected": case.phone_detected,
                    "association_score": case.association_score,
                    "context": case.context,
                    "notes": case.notes,
                })
        logger.info(f"Saved {len(self._cases)} false-positive cases to {path}")
