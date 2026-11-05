"""Evidence frame selector for VLM explanation.

Selects the most informative frames from an anomaly segment
to feed to a Vision-Language Model for explanation generation.
"""

import logging
from typing import List, Tuple, Optional
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class EvidenceSelection:
    """Selected evidence for explanation."""
    frame_indices: List[int]
    frame_scores: List[float]
    segment_start: float  # seconds
    segment_end: float    # seconds
    peak_score: float
    context: str


class EvidenceSelector:
    """Selects representative evidence frames from anomaly segments.

    Selection criteria:
    1. Peak scoring frame (highest anomaly score)
    2. Onset frame (first frame crossing threshold)
    3. Diverse frames spanning the anomaly segment
    """

    def __init__(self, top_k: int = 5, min_interval: int = 5):
        """Initialize selector.

        Args:
            top_k: Number of evidence frames to select.
            min_interval: Minimum frame interval between selected frames.
        """
        self._top_k = top_k
        self._min_interval = min_interval

    def select(
        self,
        scores: np.ndarray,
        start_frame: int,
        end_frame: int,
        fps: float = 30.0,
        context: str = "LECTURE",
    ) -> EvidenceSelection:
        """Select evidence frames from an anomaly segment.

        Args:
            scores: Full video anomaly scores (per-frame).
            start_frame: Segment start frame index.
            end_frame: Segment end frame index.
            fps: Video FPS for time conversion.
            context: Current classroom context.

        Returns:
            EvidenceSelection with selected frame indices and metadata.
        """
        segment_scores = scores[start_frame:end_frame + 1]
        n = len(segment_scores)

        if n == 0:
            return EvidenceSelection(
                frame_indices=[], frame_scores=[],
                segment_start=0, segment_end=0,
                peak_score=0, context=context,
            )

        # Select diverse top-k frames
        selected = self._diverse_top_k(segment_scores, self._top_k, self._min_interval)

        # Convert to absolute frame indices
        abs_indices = [start_frame + idx for idx in selected]
        sel_scores = [float(segment_scores[idx]) for idx in selected]

        return EvidenceSelection(
            frame_indices=abs_indices,
            frame_scores=sel_scores,
            segment_start=start_frame / fps,
            segment_end=end_frame / fps,
            peak_score=float(np.max(segment_scores)),
            context=context,
        )

    def _diverse_top_k(
        self, scores: np.ndarray, k: int, min_interval: int
    ) -> List[int]:
        """Select top-k diverse indices by score with minimum spacing."""
        sorted_indices = np.argsort(scores)[::-1]
        selected = []

        for idx in sorted_indices:
            if len(selected) >= k:
                break
            # Check minimum interval from already selected
            if all(abs(idx - s) >= min_interval for s in selected):
                selected.append(int(idx))

        return sorted(selected)
