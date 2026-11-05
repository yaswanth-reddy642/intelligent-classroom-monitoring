"""Face recognition engine — orchestrates detection, encoding, and matching."""

import logging
from typing import Dict, List, Tuple

import numpy as np

from ai_pipeline.config import FaceRecognitionConfig
from ai_pipeline.face_recognition.models import MatchResult
from ai_pipeline.face_recognition.face_detector import FaceDetector
from ai_pipeline.face_recognition.face_encoder import FaceEncoder
from ai_pipeline.face_recognition.face_database import FaceDatabase
from ai_pipeline.face_recognition.face_matcher import FaceMatcher

logger = logging.getLogger(__name__)


class FaceRecognitionEngine:
    """Main orchestrator for the face recognition pipeline.

    For each student detection:
    1. Detect face within student bounding box
    2. Extract 512-dim ArcFace embedding
    3. Match against enrolled student database
    4. Return identity assignment

    Components are lazy-initialized and share the same InsightFace app instance.
    """

    def __init__(self, config: FaceRecognitionConfig):
        self.config = config
        self._detector = None
        self._encoder = None
        self._database = None
        self._matcher = None

    def _init_components(self) -> None:
        """Lazy-initialize all face recognition components."""
        if not self._database:
            self._database = FaceDatabase(self.config)

        if not self._detector:
            self._detector = FaceDetector(self.config)

        if not self._encoder:
            self._encoder = FaceEncoder(self.config)
            # Share the InsightFace app instance between detector and encoder
            if self._detector._is_initialized and not self._encoder._is_initialized:
                self._encoder._app = self._detector._app
                self._encoder._is_initialized = True
            elif self._encoder._is_initialized and not self._detector._is_initialized:
                self._detector._app = self._encoder._app
                self._detector._is_initialized = True

        if not self._matcher:
            self._matcher = FaceMatcher(self.config, self._database)

    def recognize(
        self,
        frame: np.ndarray,
        student_bboxes: List[Tuple[float, float, float, float]],
    ) -> Dict[int, MatchResult]:
        """Recognize faces within student bounding boxes.

        Args:
            frame: Full video frame (BGR).
            student_bboxes: List of student bounding boxes (x1,y1,x2,y2).

        Returns:
            Dict mapping bbox index -> MatchResult.
        """
        results: Dict[int, MatchResult] = {}

        if not self.is_enabled:
            return results

        try:
            self._init_components()

            # Detect faces in all student bboxes
            detections = self._detector.detect_faces(frame, student_bboxes)

            for i, bbox in enumerate(student_bboxes):
                # Find the detection corresponding to this bbox
                best_det = None
                for det in detections:
                    if det.student_bbox == tuple(float(v) for v in bbox):
                        best_det = det
                        break

                if best_det:
                    embedding = self._encoder.encode(frame, best_det)
                    if embedding:
                        match = self._matcher.match(embedding.embedding)
                        results[i] = match
                    else:
                        results[i] = MatchResult(matched=False)
                else:
                    results[i] = MatchResult(matched=False)

        except Exception as e:
            logger.error(f"Error in face recognition engine: {e}")

        return results

    @property
    def is_enabled(self) -> bool:
        """Whether face recognition is enabled in config."""
        return self.config.enabled

    def get_database(self) -> FaceDatabase:
        """Get the face database instance."""
        self._init_components()
        return self._database

    def reload_database(self) -> None:
        """Reload face database from disk."""
        if self._database:
            self._database.load()
            logger.info("Face database reloaded from disk.")
