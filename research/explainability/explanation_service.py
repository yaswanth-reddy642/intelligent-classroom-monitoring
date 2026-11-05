"""Explanation service — orchestrates evidence selection and VLM explanation.

Connects the EvidenceSelector with the VLMExplainer to generate
full explanations for detected anomaly segments.
"""

import logging
from typing import List, Optional

import numpy as np
import cv2

from research.explainability.evidence_selector import EvidenceSelector, EvidenceSelection
from research.explainability.vlm_explainer import VLMExplainer, Explanation

logger = logging.getLogger(__name__)


class ExplanationService:
    """Orchestrates evidence selection and VLM explanation generation.

    Pipeline:
        Anomaly detected → select evidence frames → VLM → textual explanation

    If VLM is not configured, the service returns a basic summary without
    AI-generated text. The core anomaly detection system is independent.
    """

    def __init__(
        self,
        vlm_provider: str = "none",
        vlm_model: str = "",
        vlm_api_key: Optional[str] = None,
        top_k_frames: int = 5,
        min_frame_interval: int = 5,
    ):
        self._selector = EvidenceSelector(
            top_k=top_k_frames,
            min_interval=min_frame_interval,
        )
        self._explainer = VLMExplainer(
            provider=vlm_provider,
            model=vlm_model,
            api_key=vlm_api_key,
        )

    @property
    def vlm_enabled(self) -> bool:
        return self._explainer.is_enabled

    def explain_segment(
        self,
        video_frames: List[np.ndarray],
        scores: np.ndarray,
        start_frame: int,
        end_frame: int,
        fps: float = 30.0,
        context: str = "LECTURE",
    ) -> dict:
        """Generate explanation for an anomaly segment.

        Args:
            video_frames: All video frames (or frames in the segment range).
            scores: Per-frame anomaly scores.
            start_frame: Segment start.
            end_frame: Segment end.
            fps: Video FPS.
            context: Classroom context.

        Returns:
            Dict with selection info and explanation.
        """
        # 1. Select evidence frames
        selection = self._selector.select(
            scores, start_frame, end_frame, fps, context,
        )

        # 2. Extract actual frames
        evidence_frames = []
        for idx in selection.frame_indices:
            if 0 <= idx < len(video_frames):
                evidence_frames.append(video_frames[idx])

        # 3. Generate explanation
        explanation = self._explainer.explain(
            frames=evidence_frames,
            anomaly_score=selection.peak_score,
            context=context,
            segment_start=selection.segment_start,
            segment_end=selection.segment_end,
        )

        return {
            "selection": {
                "frame_indices": selection.frame_indices,
                "frame_scores": selection.frame_scores,
                "segment_start": selection.segment_start,
                "segment_end": selection.segment_end,
                "peak_score": selection.peak_score,
            },
            "explanation": explanation.to_dict(),
        }
