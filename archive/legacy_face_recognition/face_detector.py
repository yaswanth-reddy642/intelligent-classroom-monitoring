"""Face detector using InsightFace RetinaFace."""

import logging
from typing import List, Tuple

import numpy as np

from ai_pipeline.face_recognition.models import FaceDetectionResult
from ai_pipeline.config import FaceRecognitionConfig

logger = logging.getLogger(__name__)


class FaceDetector:
    """Detects faces within student bounding box regions using InsightFace.

    Uses RetinaFace (built into InsightFace) for face detection.
    Lazy-initializes the model on first use. Falls back gracefully
    if InsightFace is not installed.
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
            import insightface
            from insightface.app import FaceAnalysis

            providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
            self._app = FaceAnalysis(name=self.config.model_name, providers=providers)
            self._app.prepare(ctx_id=0, det_size=(640, 640))
            self._is_initialized = True
            logger.info("InsightFace FaceDetector initialized successfully.")
            return True
        except ImportError:
            logger.error(
                "InsightFace is not installed. Install with: pip install insightface onnxruntime"
            )
            return False
        except Exception as e:
            logger.error(f"Failed to initialize FaceDetector: {e}")
            return False

    def detect_faces(
        self,
        frame: np.ndarray,
        student_bboxes: List[Tuple[float, float, float, float]],
    ) -> List[FaceDetectionResult]:
        """Detect faces within given student bounding boxes.

        Args:
            frame: Full video frame (BGR).
            student_bboxes: List of student bounding boxes (x1,y1,x2,y2).

        Returns:
            List of FaceDetectionResult, one per student where a face was found.
        """
        if not self._initialize():
            return []

        results = []
        h_frame, w_frame = frame.shape[:2]

        for bbox in student_bboxes:
            x1, y1, x2, y2 = [
                int(max(0, min(v, m)))
                for v, m in zip(bbox, [w_frame, h_frame, w_frame, h_frame])
            ]
            if x2 - x1 < self.config.min_face_size or y2 - y1 < self.config.min_face_size:
                continue

            crop = frame[y1:y2, x1:x2]
            if crop.size == 0:
                continue

            try:
                faces = self._app.get(crop)
                if not faces:
                    continue

                best_face = max(faces, key=lambda f: f.det_score)
                if best_face.det_score < self.config.detection_threshold:
                    continue

                # Convert crop-relative coords back to full-frame coords
                fx1, fy1, fx2, fy2 = best_face.bbox
                full_fx1 = x1 + fx1
                full_fy1 = y1 + fy1
                full_fx2 = x1 + fx2
                full_fy2 = y1 + fy2

                landmarks = None
                if hasattr(best_face, "kps") and best_face.kps is not None:
                    landmarks = best_face.kps + np.array([x1, y1])
                elif hasattr(best_face, "landmark_2d_106") and best_face.landmark_2d_106 is not None:
                    landmarks = best_face.landmark_2d_106 + np.array([x1, y1])

                results.append(
                    FaceDetectionResult(
                        face_bbox=(float(full_fx1), float(full_fy1), float(full_fx2), float(full_fy2)),
                        face_confidence=float(best_face.det_score),
                        student_bbox=tuple(float(v) for v in bbox),
                        landmarks=landmarks,
                    )
                )
            except Exception as e:
                logger.warning(f"Error detecting face in crop: {e}")

        return results

    def detect_faces_full_frame(self, frame: np.ndarray) -> List[FaceDetectionResult]:
        """Detect all faces in the entire frame (used for enrollment).

        Args:
            frame: Full image (BGR).

        Returns:
            List of FaceDetectionResult for each detected face.
        """
        if not self._initialize():
            return []

        results = []
        try:
            faces = self._app.get(frame)
            for face in faces:
                if face.det_score < self.config.detection_threshold:
                    continue

                fx1, fy1, fx2, fy2 = face.bbox
                landmarks = None
                if hasattr(face, "kps") and face.kps is not None:
                    landmarks = face.kps

                results.append(
                    FaceDetectionResult(
                        face_bbox=(float(fx1), float(fy1), float(fx2), float(fy2)),
                        face_confidence=float(face.det_score),
                        student_bbox=(float(fx1), float(fy1), float(fx2), float(fy2)),
                        landmarks=landmarks,
                    )
                )
        except Exception as e:
            logger.error(f"Error detecting faces in full frame: {e}")

        return results
