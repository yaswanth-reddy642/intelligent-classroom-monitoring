"""Vision-Language Model explainer for anomaly events.

Generates human-readable textual explanations for detected anomalies
using a configurable VLM provider. The VLM is an explanation layer only
and does NOT override the anomaly detector.

Supported providers: openai (GPT-4V), google (Gemini), local (placeholder).
If no VLM is configured, the core detection system continues working.
"""

import logging
import base64
import os
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

import cv2
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class Explanation:
    """VLM-generated explanation for an anomaly event."""
    text: str
    model_used: str
    evidence_frame_count: int
    anomaly_score: float
    timestamp: float
    confidence_note: str = ""

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "model_used": self.model_used,
            "evidence_frame_count": self.evidence_frame_count,
            "anomaly_score": round(self.anomaly_score, 4),
            "timestamp": self.timestamp,
            "confidence_note": self.confidence_note,
        }


class VLMExplainer:
    """Generates textual explanations for anomaly events using a VLM.

    The VLM does NOT override the anomaly detector. It provides
    supplementary explanation only.
    """

    SYSTEM_PROMPT = (
        "You are analyzing video frames from a classroom monitoring system. "
        "The system has detected potential anomalous activity. "
        "Describe what you observe in the provided frames objectively. "
        "Do NOT claim certainty about student behavior or intent. "
        "Use phrases like 'appears to be', 'a person seems to', 'potential'. "
        "Do NOT identify individuals by name or make accusations. "
        "Focus on observable actions only."
    )

    def __init__(
        self,
        provider: str = "none",
        model: str = "",
        api_key: Optional[str] = None,
    ):
        """Initialize VLM explainer.

        Args:
            provider: VLM provider ('openai', 'google', 'none').
            model: Model name (e.g., 'gpt-4o', 'gemini-1.5-flash').
            api_key: API key (or set via environment variable).
        """
        self._provider = provider
        self._model = model
        self._api_key = api_key or os.environ.get("VLM_API_KEY", "")
        self._enabled = provider != "none" and bool(self._api_key)

        if self._enabled:
            logger.info(f"VLMExplainer enabled: provider={provider}, model={model}")
        else:
            logger.info("VLMExplainer disabled (no provider/API key configured)")

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    def explain(
        self,
        frames: List[np.ndarray],
        anomaly_score: float,
        context: str = "LECTURE",
        segment_start: float = 0.0,
        segment_end: float = 0.0,
    ) -> Explanation:
        """Generate explanation for evidence frames.

        Args:
            frames: List of BGR evidence frames.
            anomaly_score: Anomaly score for the segment.
            context: Classroom context mode.
            segment_start: Segment start time (seconds).
            segment_end: Segment end time (seconds).

        Returns:
            Explanation with generated text.
        """
        if not self._enabled:
            return Explanation(
                text="VLM explanation not available (not configured).",
                model_used="none",
                evidence_frame_count=len(frames),
                anomaly_score=anomaly_score,
                timestamp=segment_start,
                confidence_note="VLM is disabled. Core detection is independent.",
            )

        try:
            prompt = (
                f"The classroom monitoring system detected potential anomalous "
                f"activity between {segment_start:.1f}s and {segment_end:.1f}s "
                f"with an anomaly score of {anomaly_score:.2f}. "
                f"The classroom context is {context}. "
                f"Describe what you observe in these {len(frames)} evidence frames."
            )

            if self._provider == "openai":
                text = self._call_openai(frames, prompt)
            elif self._provider == "google":
                text = self._call_google(frames, prompt)
            else:
                text = f"Potential anomalous activity detected (score: {anomaly_score:.2f}). VLM provider '{self._provider}' not implemented."

            return Explanation(
                text=text,
                model_used=f"{self._provider}/{self._model}",
                evidence_frame_count=len(frames),
                anomaly_score=anomaly_score,
                timestamp=segment_start,
                confidence_note="This is an AI-generated description, not a definitive assessment.",
            )

        except Exception as e:
            logger.error(f"VLM explanation error: {e}")
            return Explanation(
                text=f"Explanation generation failed: {e}",
                model_used=self._provider,
                evidence_frame_count=len(frames),
                anomaly_score=anomaly_score,
                timestamp=segment_start,
                confidence_note="Error during explanation generation.",
            )

    def _frames_to_base64(self, frames: List[np.ndarray]) -> List[str]:
        """Convert frames to base64-encoded JPEG strings."""
        encoded = []
        for frame in frames:
            _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            encoded.append(base64.b64encode(buffer).decode("utf-8"))
        return encoded

    def _call_openai(self, frames: List[np.ndarray], prompt: str) -> str:
        """Call OpenAI GPT-4V API."""
        from openai import OpenAI
        client = OpenAI(api_key=self._api_key)

        images = self._frames_to_base64(frames)
        content = [{"type": "text", "text": prompt}]
        for img_b64 in images:
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"},
            })

        response = client.chat.completions.create(
            model=self._model or "gpt-4o",
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": content},
            ],
            max_tokens=300,
        )
        return response.choices[0].message.content

    def _call_google(self, frames: List[np.ndarray], prompt: str) -> str:
        """Call Google Gemini API."""
        import google.generativeai as genai
        genai.configure(api_key=self._api_key)
        model = genai.GenerativeModel(self._model or "gemini-1.5-flash")

        from PIL import Image
        import io
        pil_images = []
        for frame in frames:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_images.append(Image.fromarray(rgb))

        content = [self.SYSTEM_PROMPT + "\n\n" + prompt] + pil_images
        response = model.generate_content(content)
        return response.text
