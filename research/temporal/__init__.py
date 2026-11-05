"""Temporal anomaly localization.

Identifies when anomalies occurred within a video sequence,
producing start/end timestamps and evidence segments.
"""

import logging
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class AnomalySegment:
    """A localized anomaly segment within a video."""
    start_time: float       # seconds
    end_time: float         # seconds
    start_frame: int
    end_frame: int
    max_score: float        # peak anomaly score in segment
    mean_score: float       # average anomaly score in segment
    segment_scores: List[float] = field(default_factory=list)
    evidence_frame_indices: List[int] = field(default_factory=list)

    @property
    def duration(self) -> float:
        return self.end_time - self.start_time

    def to_dict(self) -> dict:
        return {
            "start_time": round(self.start_time, 2),
            "end_time": round(self.end_time, 2),
            "start_frame": self.start_frame,
            "end_frame": self.end_frame,
            "duration": round(self.duration, 2),
            "max_score": round(self.max_score, 4),
            "mean_score": round(self.mean_score, 4),
            "evidence_frame_indices": self.evidence_frame_indices,
        }


@dataclass
class LocalizationResult:
    """Full localization result for a video."""
    segments: List[AnomalySegment]
    total_duration: float
    anomaly_ratio: float  # fraction of time in anomaly
    timeline: List[dict] = field(default_factory=list)  # per-segment labels

    def to_dict(self) -> dict:
        return {
            "segments": [s.to_dict() for s in self.segments],
            "total_duration": round(self.total_duration, 2),
            "anomaly_ratio": round(self.anomaly_ratio, 4),
            "num_anomalies": len(self.segments),
            "timeline": self.timeline,
        }


class TemporalLocalizer:
    """Localizes anomalies temporally within a sequence of scores.

    Takes a sequence of per-frame or per-segment anomaly scores
    and identifies contiguous anomaly regions.
    """

    def __init__(
        self,
        threshold: float = 0.5,
        min_duration: float = 1.0,
        merge_gap: float = 2.0,
        fps: float = 30.0,
        top_k_evidence: int = 3,
    ):
        """Initialize the localizer.

        Args:
            threshold: Score threshold for anomaly classification.
            min_duration: Minimum anomaly segment duration (seconds).
            merge_gap: Maximum gap (seconds) to merge adjacent segments.
            fps: Video frame rate for time conversion.
            top_k_evidence: Number of top-scoring evidence frames per segment.
        """
        self._threshold = threshold
        self._min_duration = min_duration
        self._merge_gap = merge_gap
        self._fps = fps
        self._top_k = top_k_evidence

    def localize(
        self,
        scores: np.ndarray,
        fps: Optional[float] = None,
    ) -> LocalizationResult:
        """Localize anomalies in a score sequence.

        Args:
            scores: 1D array of anomaly scores, one per frame/segment.
            fps: Override frame rate for this call.

        Returns:
            LocalizationResult with identified anomaly segments.
        """
        fps = fps or self._fps
        n = len(scores)
        if n == 0:
            return LocalizationResult(segments=[], total_duration=0.0,
                                       anomaly_ratio=0.0)

        total_duration = n / fps

        # Step 1: Find contiguous anomaly regions above threshold
        is_anomaly = scores >= self._threshold
        raw_segments = self._find_contiguous(is_anomaly, scores, fps)

        # Step 2: Merge nearby segments
        merged = self._merge_segments(raw_segments, fps)

        # Step 3: Filter by minimum duration
        filtered = [s for s in merged if s.duration >= self._min_duration]

        # Step 4: Extract evidence frames (top-k scoring frames per segment)
        for seg in filtered:
            seg_scores = scores[seg.start_frame:seg.end_frame + 1]
            if len(seg_scores) > 0:
                top_indices = np.argsort(seg_scores)[-self._top_k:][::-1]
                seg.evidence_frame_indices = [
                    int(seg.start_frame + idx) for idx in top_indices
                ]

        # Step 5: Build timeline
        timeline = self._build_timeline(filtered, total_duration, fps)

        # Anomaly ratio
        anomaly_frames = sum(s.end_frame - s.start_frame + 1 for s in filtered)
        anomaly_ratio = anomaly_frames / n if n > 0 else 0.0

        return LocalizationResult(
            segments=filtered,
            total_duration=total_duration,
            anomaly_ratio=anomaly_ratio,
            timeline=timeline,
        )

    def _find_contiguous(
        self, mask: np.ndarray, scores: np.ndarray, fps: float
    ) -> List[AnomalySegment]:
        """Find contiguous True regions in a boolean mask."""
        segments = []
        in_segment = False
        start = 0

        for i in range(len(mask)):
            if mask[i] and not in_segment:
                start = i
                in_segment = True
            elif not mask[i] and in_segment:
                seg_scores = scores[start:i].tolist()
                segments.append(AnomalySegment(
                    start_time=start / fps,
                    end_time=i / fps,
                    start_frame=start,
                    end_frame=i - 1,
                    max_score=float(np.max(seg_scores)),
                    mean_score=float(np.mean(seg_scores)),
                    segment_scores=seg_scores,
                ))
                in_segment = False

        # Handle segment at end
        if in_segment:
            seg_scores = scores[start:].tolist()
            segments.append(AnomalySegment(
                start_time=start / fps,
                end_time=len(mask) / fps,
                start_frame=start,
                end_frame=len(mask) - 1,
                max_score=float(np.max(seg_scores)),
                mean_score=float(np.mean(seg_scores)),
                segment_scores=seg_scores,
            ))

        return segments

    def _merge_segments(
        self, segments: List[AnomalySegment], fps: float
    ) -> List[AnomalySegment]:
        """Merge nearby segments within merge_gap."""
        if len(segments) <= 1:
            return segments

        merged = [segments[0]]
        for seg in segments[1:]:
            prev = merged[-1]
            gap = seg.start_time - prev.end_time
            if gap <= self._merge_gap:
                # Merge
                all_scores = prev.segment_scores + seg.segment_scores
                merged[-1] = AnomalySegment(
                    start_time=prev.start_time,
                    end_time=seg.end_time,
                    start_frame=prev.start_frame,
                    end_frame=seg.end_frame,
                    max_score=max(prev.max_score, seg.max_score),
                    mean_score=float(np.mean(all_scores)),
                    segment_scores=all_scores,
                )
            else:
                merged.append(seg)

        return merged

    def _build_timeline(
        self, segments: List[AnomalySegment], total_duration: float, fps: float
    ) -> List[dict]:
        """Build a human-readable timeline of normal/anomaly periods."""
        timeline = []
        prev_end = 0.0

        for seg in sorted(segments, key=lambda s: s.start_time):
            if seg.start_time > prev_end:
                timeline.append({
                    "start": round(prev_end, 2),
                    "end": round(seg.start_time, 2),
                    "label": "NORMAL",
                })
            timeline.append({
                "start": round(seg.start_time, 2),
                "end": round(seg.end_time, 2),
                "label": "ANOMALY",
                "max_score": round(seg.max_score, 4),
            })
            prev_end = seg.end_time

        if prev_end < total_duration:
            timeline.append({
                "start": round(prev_end, 2),
                "end": round(total_duration, 2),
                "label": "NORMAL",
            })

        return timeline
