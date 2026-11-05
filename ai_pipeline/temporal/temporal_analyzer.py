from typing import Dict, Any, List
import collections
import time


class TemporalAnalyzer:
    def __init__(self, window_seconds: int = 10, min_consecutive: int = 3):
        self.window = window_seconds
        self.min_consecutive = min_consecutive
        # store per student: deque of (timestamp, phone_detected, assoc_score)
        self.history = collections.defaultdict(collections.deque)

    def update(self, timestamp: float, student_id: str, phone_detected: bool, assoc_score: float):
        dq = self.history[student_id]
        dq.append((timestamp, phone_detected, assoc_score))
        # drop older than window
        while dq and (timestamp - dq[0][0]) > self.window:
            dq.popleft()

    def compute_persistence(self, student_id: str) -> Dict[str, Any]:
        dq = self.history.get(student_id, [])
        if not dq:
            return {"persistence": 0.0, "consecutive": 0}
        consecutive = 0
        max_consec = 0
        for _, phone_detected, _ in dq:
            if phone_detected:
                consecutive += 1
                max_consec = max(max_consec, consecutive)
            else:
                consecutive = 0
        persistence = sum(1 for item in dq if item[1]) / len(dq)
        return {"persistence": persistence, "consecutive": max_consec}
"""Temporal behavior analyzer for phone usage persistence.

Maintains a sliding time-series window per student and computes
temporal metrics. Anomaly decisions are NEVER made from a single frame.
"""

import logging
import time
from collections import defaultdict, deque
from typing import Dict, Optional

from ai_pipeline.config import TemporalConfig
from ai_pipeline.temporal.models import TemporalRecord, TemporalProfile

logger = logging.getLogger(__name__)


class TemporalAnalyzer:
    """Analyzes phone usage behavior over time per student.

    Maintains a sliding window of observations and computes:
    - persistence ratio
    - consecutive detection count
    - average confidence/association scores
    - detection consistency
    """

    def __init__(self, config: TemporalConfig):
        self._config = config
        # Per-student sliding window: tracking_id -> deque of TemporalRecord
        self._windows: Dict[int, deque] = defaultdict(deque)

    def record(
        self,
        student_tracking_id: int,
        phone_detected: bool,
        phone_confidence: float = 0.0,
        association_score: float = 0.0,
    ) -> None:
        """Record an observation for a student.

        Args:
            student_tracking_id: ByteTrack tracking ID.
            phone_detected: Whether a phone is associated this frame.
            phone_confidence: Phone detection confidence.
            association_score: Student-phone association score.
        """
        now = time.time()
        record = TemporalRecord(
            timestamp=now,
            student_tracking_id=student_tracking_id,
            phone_detected=phone_detected,
            phone_confidence=phone_confidence,
            association_score=association_score,
        )
        window = self._windows[student_tracking_id]
        window.append(record)

        # Prune records outside the temporal window
        cutoff = now - self._config.temporal_window
        while window and window[0].timestamp < cutoff:
            window.popleft()

    def get_profile(self, student_tracking_id: int) -> TemporalProfile:
        """Compute the temporal profile for a student.

        Args:
            student_tracking_id: ByteTrack tracking ID.

        Returns:
            TemporalProfile with aggregated temporal metrics.
        """
        window = self._windows.get(student_tracking_id, deque())
        profile = TemporalProfile(student_tracking_id=student_tracking_id)

        if not window:
            return profile

        records = list(window)
        total = len(records)
        phone_records = [r for r in records if r.phone_detected]
        phone_count = len(phone_records)

        # Window size
        profile.window_size = records[-1].timestamp - records[0].timestamp if total > 1 else 0

        # Persistence ratio
        profile.persistence_ratio = phone_count / total if total > 0 else 0.0

        # Total duration with phone (estimated from frame timestamps)
        if phone_count > 1:
            phone_timestamps = [r.timestamp for r in phone_records]
            profile.total_duration = phone_timestamps[-1] - phone_timestamps[0]
        elif phone_count == 1:
            profile.total_duration = 0.0

        # Consecutive detections (current streak from end)
        consecutive = 0
        for r in reversed(records):
            if r.phone_detected:
                consecutive += 1
            else:
                break
        profile.consecutive_detections = consecutive

        # Max consecutive in window
        max_consec = 0
        current_consec = 0
        for r in records:
            if r.phone_detected:
                current_consec += 1
                max_consec = max(max_consec, current_consec)
            else:
                current_consec = 0
        profile.max_consecutive = max_consec

        # Average confidence and association scores
        if phone_count > 0:
            profile.avg_phone_confidence = sum(r.phone_confidence for r in phone_records) / phone_count
            profile.avg_association_score = sum(r.association_score for r in phone_records) / phone_count

        # Detection consistency: ratio of max_consecutive to total records
        profile.detection_consistency = max_consec / total if total > 0 else 0.0

        return profile

    def meets_threshold(self, student_tracking_id: int) -> bool:
        """Check if a student's phone usage meets the minimum temporal threshold.

        Returns True only when:
        - Duration exceeds min_phone_duration
        - Consecutive detections exceed min_consecutive_detections
        - Persistence ratio exceeds persistence_threshold
        """
        profile = self.get_profile(student_tracking_id)

        return (
            profile.total_duration >= self._config.min_phone_duration
            and profile.consecutive_detections >= self._config.min_consecutive_detections
            and profile.persistence_ratio >= self._config.persistence_threshold
        )

    def get_all_profiles(self) -> Dict[int, TemporalProfile]:
        """Get temporal profiles for all tracked students."""
        return {tid: self.get_profile(tid) for tid in self._windows}

    def remove_student(self, student_tracking_id: int) -> None:
        """Remove temporal data for a student."""
        self._windows.pop(student_tracking_id, None)

    def reset(self) -> None:
        """Clear all temporal data."""
        self._windows.clear()
