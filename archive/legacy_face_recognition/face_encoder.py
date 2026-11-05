"""Face embedding extractor using InsightFace ArcFace."""

import logging
from typing import Optional

import numpy as np

from ai_pipeline.face_recognition.models import FaceDetectionResult, FaceEmbedding
from ai_pipeline.config import FaceRecognitionConfig

logger = logging.getLogger(__name__)


class FaceEncoder:
    """Extracts 512-dimensional face embeddings using ArcFace via InsightFace.

    Shares the InsightFace FaceAnalysis app with FaceDetector when possible.
    """

    def __init__(self, config: FaceRecognitionConfig):
        self.config = config
        self._app = None
        self._is_initialized = False

    def _initialize(self) -> bool:
        """Lazy-initialize the InsightFace app."""
        if self._is_initialized:
            return True

        try:
            from insightface.app import FaceAnalysis

            providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
            self._app = FaceAnalysis(name=self.config.model_name, providers=providers)
            self._app.prepare(ctx_id=0, det_size=(640, 640))
            self._is_initialized = True
            logger.info("InsightFace FaceEncoder initialized successfully.")
            return True
        except ImportError:
            logger.error(
                "InsightFace is not installed. Install with: pip install insightface onnxruntime"
            )
            return False
        except Exception as e:
            logger.error(f"Failed to initialize FaceEncoder: {e}")
            return False

    def encode(
        self, frame: np.ndarray, face_detection: FaceDetectionResult
    ) -> Optional[FaceEmbedding]:
        """Extract embedding from a detected face region.

        Args:
            frame: Full video frame (BGR).
            face_detection: Face detection result with bbox coords.

        Returns:
            FaceEmbedding or None if extraction failed.
        """
        if not self._initialize():
            return None

        try:
            h_frame, w_frame = frame.shape[:2]
            fx1, fy1, fx2, fy2 = [int(v) for v in face_detection.face_bbox]

            # Add 20% margin for better embedding quality
            w, h = fx2 - fx1, fy2 - fy1
            mx, my = int(w * 0.2), int(h * 0.2)
            cx1 = max(0, fx1 - mx)
            cy1 = max(0, fy1 - my)
            cx2 = min(w_frame, fx2 + mx)
            cy2 = min(h_frame, fy2 + my)

            face_crop = frame[cy1:cy2, cx1:cx2]
            if face_crop.size == 0:
                return None

            faces = self._app.get(face_crop)
            if not faces:
                return None

            best_face = max(faces, key=lambda f: f.det_score)
            if hasattr(best_face, "embedding") and best_face.embedding is not None:
                emb = best_face.embedding.copy()
                norm = np.linalg.norm(emb)
                if norm > 0:
                    emb = emb / norm
                return FaceEmbedding(embedding=emb, quality_score=float(best_face.det_score))

        except Exception as e:
            logger.warning(f"Error encoding face: {e}")

        return None

    def encode_from_image(self, image: np.ndarray) -> Optional[FaceEmbedding]:
        """Extract embedding from a standalone image (used for enrollment).

        Args:
            image: Full image (BGR) containing exactly one face.

        Returns:
            FaceEmbedding or None if no suitable face found.
        """
        if not self._initialize():
            return None

        try:
            faces = self._app.get(image)
            if not faces:
                return None

            best_face = max(faces, key=lambda f: f.det_score)
            if best_face.det_score < self.config.detection_threshold:
                return None

            if hasattr(best_face, "embedding") and best_face.embedding is not None:
                emb = best_face.embedding.copy()
                norm = np.linalg.norm(emb)
                if norm > 0:
                    emb = emb / norm
                return FaceEmbedding(embedding=emb, quality_score=float(best_face.det_score))

        except Exception as e:
            logger.warning(f"Error encoding face from image: {e}")

        return None
