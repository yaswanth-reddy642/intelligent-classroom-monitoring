"""Configurable anomaly scoring engine.

Computes: A = w1*D + w2*S + w3*T + w4*C
where D=phone confidence, S=association, T=temporal, C=context.
All weights and thresholds come from configuration.
"""

import logging
from ai_pipeline.config import AnomalyConfig
from ai_pipeline.anomaly.models import AnomalyResult, AnomalyClassification

logger = logging.getLogger(__name__)


class AnomalyScorer:
    """Computes anomaly scores from pipeline component outputs.

    Formula: A = w1*D + w2*S + w3*T + w4*C

    Each component is normalized to [0, 1] before weighting.
    The final score is clamped to [0, 1].
    """

    def __init__(self, config: AnomalyConfig):
        self._config = config

    def score(
        self,
        phone_confidence: float = 0.0,
        association_score: float = 0.0,
        temporal_persistence: float = 0.0,
        context_multiplier: float = 1.0,
        consecutive_detections: int = 1,
        total_duration: float = 0.0,
    ) -> AnomalyResult:
        """Compute anomaly score for a student with temporal confirmation.

        Args:
            phone_confidence: Phone detection confidence [0, 1].
            association_score: Student-phone association score [0, 1].
            temporal_persistence: Temporal persistence ratio [0, 1].
            context_multiplier: Classroom context multiplier (e.g. 1.5 for EXAM).
            consecutive_detections: Consecutive frames phone was associated.
            total_duration: Total seconds phone observed with student.

        Returns:
            AnomalyResult with score, classification, and reasons.
        """
        # 1. Zero-guard: if no phone is detected or association is weak, score is strictly 0.0 (Normal)
        if phone_confidence < 0.22 or association_score < 0.25:
            return AnomalyResult(
                score=0.0,
                classification=AnomalyClassification.NORMAL,
                reasons=[],
                components={
                    "phone_confidence": 0.0,
                    "association_score": 0.0,
                    "temporal_persistence": 0.0,
                    "context_multiplier": context_multiplier,
                    "consecutive_detections": consecutive_detections,
                    "raw_score": 0.0,
                },
            )

        # 2. Check if detection is momentary / single-frame
        # If seen for fewer than 3 consecutive frames or < 1.0s, cap at SUSPICIOUS (prevent abnormal alert spam)
        is_sustained = (consecutive_detections >= 3 or total_duration >= 1.0)

        # 3. Violation score combines phone detection, spatial proximity, and real temporal persistence
        temporal_factor = min(temporal_persistence * 1.5, 1.0) if is_sustained else 0.20
        base_violation = (
            0.38 * phone_confidence
            + 0.38 * association_score
            + 0.24 * temporal_factor
        )

        # Scale by context multiplier (e.g. 1.0 Lecture, 1.5 Exam, 0.2 Break)
        score = min(1.0, max(0.0, round(base_violation * context_multiplier, 3)))

        # If not sustained over time, cap score below anomaly threshold (at most 0.50 -> SUSPICIOUS)
        if not is_sustained:
            score = min(score, 0.50)

        # Build detailed reasons
        reasons = []
        if phone_confidence >= 0.50:
            reasons.append(f"Phone detected ({int(phone_confidence * 100)}% confidence)")
        elif phone_confidence >= 0.22:
            reasons.append(f"Mobile device detected ({int(phone_confidence * 100)}% confidence)")

        if association_score >= 0.50:
            reasons.append("Close proximity to student hand/desk")
        elif association_score >= 0.25:
            reasons.append("Device detected in student proximity")

        if is_sustained:
            reasons.append(f"Sustained device interaction ({consecutive_detections} frames, {total_duration:.1f}s)")
        else:
            reasons.append("Brief device sighting (monitoring persistence)")

        if context_multiplier >= 1.5:
            reasons.append("Exam mode: zero tolerance violation")
        elif context_multiplier <= 0.2:
            reasons.append("Break mode: alerts suppressed")

        # Classify
        thresholds = self._config.thresholds
        if score >= thresholds.anomaly and is_sustained:
            classification = AnomalyClassification.POTENTIAL_ANOMALY
        elif score >= thresholds.suspicious or (phone_confidence >= 0.40 and association_score >= 0.40):
            classification = AnomalyClassification.SUSPICIOUS
        else:
            classification = AnomalyClassification.NORMAL

        return AnomalyResult(
            score=score,
            classification=classification,
            reasons=reasons,
            components={
                "phone_confidence": phone_confidence,
                "association_score": association_score,
                "temporal_persistence": temporal_persistence,
                "context_multiplier": context_multiplier,
                "consecutive_detections": consecutive_detections,
                "raw_score": base_violation,
            },
        )
