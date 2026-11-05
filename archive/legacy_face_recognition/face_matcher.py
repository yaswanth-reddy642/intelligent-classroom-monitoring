"""Face matcher using cosine similarity against enrolled embeddings."""

import logging
import numpy as np

from ai_pipeline.config import FaceRecognitionConfig
from ai_pipeline.face_recognition.face_database import FaceDatabase
from ai_pipeline.face_recognition.models import MatchResult

logger = logging.getLogger(__name__)


class FaceMatcher:
    """Matches face embeddings against the enrolled student database.

    Uses vectorized cosine similarity (dot product of L2-normalized
    embeddings) for fast batch comparison.
    """

    def __init__(self, config: FaceRecognitionConfig, database: FaceDatabase):
        self.config = config
        self.database = database

    def match(self, embedding: np.ndarray) -> MatchResult:
        """Compare an embedding against all enrolled embeddings.

        Args:
            embedding: 512-dim L2-normalized face embedding.

        Returns:
            MatchResult with matched=True if similarity >= threshold.
        """
        if embedding is None or not self.database.student_count:
            return MatchResult(matched=False)

        all_embeddings, student_ids = self.database.get_all_embeddings()

        if len(student_ids) == 0:
            return MatchResult(matched=False)

        try:
            # Vectorized cosine similarity (embeddings are L2-normalized)
            similarities = np.dot(all_embeddings, embedding)

            max_idx = int(np.argmax(similarities))
            max_similarity = float(similarities[max_idx])

            if max_similarity >= self.config.similarity_threshold:
                matched_student_id = student_ids[max_idx]
                student = self.database.get_student(matched_student_id)

                if student:
                    return MatchResult(
                        matched=True,
                        student_id=student.student_id,
                        student_name=student.name,
                        roll_number=student.roll_number,
                        department=student.department,
                        section=student.section,
                        similarity_score=max_similarity,
                    )

            return MatchResult(matched=False, similarity_score=max_similarity)

        except Exception as e:
            logger.error(f"Error matching face embedding: {e}")
            return MatchResult(matched=False)
