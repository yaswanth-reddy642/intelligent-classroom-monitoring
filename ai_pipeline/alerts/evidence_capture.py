"""Evidence frame capture for anomaly events.

Saves annotated evidence frames when high-confidence anomalies
are detected. Organized by date for easy browsing.
"""

import logging
import os
from datetime import datetime
from typing import Optional

import cv2
import numpy as np

from ai_pipeline.config import AlertConfig

logger = logging.getLogger(__name__)


class EvidenceCapture:
    """Captures and stores evidence frames for anomaly events.

    Storage layout:
        evidence_path/
            YYYY/
                MM/
                    DD/
                        CAM01_STU001_RahulSharma_2026-08-19_104215.jpg
    """

    def __init__(self, config: AlertConfig):
        self._config = config
        self._base_path = config.evidence_path
        os.makedirs(self._base_path, exist_ok=True)

    def capture(
        self,
        frame: np.ndarray,
        camera_id: str,
        student_display_id: str,
        student_name: Optional[str] = None,
    ) -> Optional[str]:
        """Capture an evidence frame.

        Args:
            frame: Annotated video frame (BGR).
            camera_id: Camera identifier.
            student_display_id: Student tracking/enrolled ID.
            student_name: Student name if known.

        Returns:
            Path to the saved evidence file, or None on failure.
        """
        if not self._config.evidence_capture:
            return None

        try:
            now = datetime.now()

            # Build directory path: evidence/YYYY/MM/DD/
            date_dir = os.path.join(
                self._base_path,
                now.strftime("%Y"),
                now.strftime("%m"),
                now.strftime("%d"),
            )
            os.makedirs(date_dir, exist_ok=True)

            # Build filename
            cam = camera_id.replace("-", "")
            stu = student_display_id.replace("-", "")
            name_part = ""
            if student_name:
                name_part = f"_{student_name.replace(' ', '')}"
            timestamp = now.strftime("%Y-%m-%d_%H%M%S")

            filename = f"{cam}_{stu}{name_part}_{timestamp}.jpg"
            filepath = os.path.join(date_dir, filename)

            cv2.imwrite(filepath, frame)
            logger.info(f"Evidence captured: {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"Failed to capture evidence: {e}")
            return None
