"""Face database for enrolled student profiles and embeddings.

Stores student profiles as JSON and face embeddings as .npy files
on disk. Syncs with MongoDB via the backend for full persistence.
"""

import os
import json
import logging
import time
from typing import Dict, List, Tuple, Optional

import numpy as np

from ai_pipeline.face_recognition.models import StudentProfile
from ai_pipeline.config import FaceRecognitionConfig

logger = logging.getLogger(__name__)


class FaceDatabase:
    """Manages enrolled student profiles and face embeddings on disk.

    Storage layout:
        face_database_path/
            profiles.json        — student profile metadata
            embeddings/
                STU-001.npy      — numpy arrays of embeddings per student
            photos/
                STU-001/
                    enroll_0.jpg — enrollment photos
    """

    def __init__(self, config: FaceRecognitionConfig):
        self.config = config
        self._profiles: Dict[str, StudentProfile] = {}

        self.db_path = config.face_database_path
        self.embeddings_dir = os.path.join(self.db_path, "embeddings")
        self.photos_dir = os.path.join(self.db_path, "photos")
        self.profiles_path = os.path.join(self.db_path, "profiles.json")

        os.makedirs(self.embeddings_dir, exist_ok=True)
        os.makedirs(self.photos_dir, exist_ok=True)

        self.load()

    def add_student(self, profile: StudentProfile) -> bool:
        """Add a new student to the database."""
        self._profiles[profile.student_id] = profile
        self.save()
        logger.info(f"Added student: {profile.student_id} ({profile.name})")
        return True

    def remove_student(self, student_id: str) -> bool:
        """Remove a student from the database."""
        if student_id in self._profiles:
            del self._profiles[student_id]
            # Remove embedding file
            emb_file = os.path.join(self.embeddings_dir, f"{student_id}.npy")
            if os.path.exists(emb_file):
                os.remove(emb_file)
            self.save()
            logger.info(f"Removed student: {student_id}")
            return True
        return False

    def update_student(self, student_id: str, **kwargs) -> bool:
        """Update fields of an existing student profile."""
        if student_id not in self._profiles:
            return False

        profile = self._profiles[student_id]
        for key, value in kwargs.items():
            if hasattr(profile, key):
                setattr(profile, key, value)

        profile.updated_at = time.time()
        self.save()
        return True

    def add_embedding(
        self, student_id: str, embedding: np.ndarray, photo_path: str = ""
    ) -> bool:
        """Add a new face embedding to an existing student."""
        if student_id not in self._profiles:
            return False

        profile = self._profiles[student_id]
        if len(profile.face_embeddings) >= self.config.max_faces_per_student:
            logger.warning(
                f"Student {student_id} has reached max embeddings "
                f"({self.config.max_faces_per_student}). Not adding."
            )
            return False

        profile.face_embeddings.append(embedding)
        if photo_path:
            profile.photo_paths.append(photo_path)

        profile.updated_at = time.time()
        self.save()
        return True

    def get_student(self, student_id: str) -> Optional[StudentProfile]:
        """Get a student profile by ID."""
        return self._profiles.get(student_id)

    def get_all_students(self) -> List[StudentProfile]:
        """Get all enrolled student profiles."""
        return list(self._profiles.values())

    def get_all_embeddings(self) -> Tuple[np.ndarray, List[str]]:
        """Get all embeddings as a matrix for batch matching.

        Returns:
            Tuple of (N x 512 embedding matrix, list of student_ids).
            Returns empty array if no embeddings exist.
        """
        embeddings_list = []
        student_ids = []

        for student_id, profile in self._profiles.items():
            if not profile.is_active:
                continue
            for emb in profile.face_embeddings:
                embeddings_list.append(emb)
                student_ids.append(student_id)

        if not embeddings_list:
            return np.empty((0, self.config.embedding_dimension)), []

        return np.vstack(embeddings_list), student_ids

    def save(self) -> None:
        """Persist profiles and embeddings to disk."""
        profiles_dict = {}

        for student_id, profile in self._profiles.items():
            # Save embeddings as .npy
            emb_file = os.path.join(self.embeddings_dir, f"{student_id}.npy")
            if profile.face_embeddings:
                np.save(emb_file, np.stack(profile.face_embeddings))

            profiles_dict[student_id] = {
                "student_id": profile.student_id,
                "name": profile.name,
                "roll_number": profile.roll_number,
                "department": profile.department,
                "section": profile.section,
                "semester": profile.semester,
                "photo_paths": profile.photo_paths,
                "enrolled_at": profile.enrolled_at,
                "updated_at": profile.updated_at,
                "is_active": profile.is_active,
            }

        try:
            with open(self.profiles_path, "w", encoding="utf-8") as f:
                json.dump(profiles_dict, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to save profiles.json: {e}")

    def load(self) -> None:
        """Load profiles and embeddings from disk."""
        if not os.path.exists(self.profiles_path):
            return

        try:
            with open(self.profiles_path, "r", encoding="utf-8") as f:
                profiles_dict = json.load(f)

            for student_id, data in profiles_dict.items():
                profile = StudentProfile(
                    student_id=data.get("student_id", student_id),
                    name=data.get("name", ""),
                    roll_number=data.get("roll_number", ""),
                    department=data.get("department", ""),
                    section=data.get("section", ""),
                    semester=data.get("semester", 0),
                    photo_paths=data.get("photo_paths", []),
                    enrolled_at=data.get("enrolled_at", 0),
                    updated_at=data.get("updated_at", 0),
                    is_active=data.get("is_active", True),
                )

                # Load embeddings from .npy
                emb_file = os.path.join(self.embeddings_dir, f"{student_id}.npy")
                if os.path.exists(emb_file):
                    embs = np.load(emb_file)
                    profile.face_embeddings = [embs[i] for i in range(embs.shape[0])]

                self._profiles[student_id] = profile

            logger.info(f"Loaded {len(self._profiles)} student profiles from disk.")
        except Exception as e:
            logger.error(f"Failed to load profiles.json: {e}")

    def generate_student_id(self) -> str:
        """Generate next available STU-XXX student ID."""
        if not self._profiles:
            return "STU-001"

        max_id = 0
        for sid in self._profiles.keys():
            if sid.startswith("STU-"):
                try:
                    max_id = max(max_id, int(sid[4:]))
                except ValueError:
                    pass

        return f"STU-{max_id + 1:03d}"

    @property
    def student_count(self) -> int:
        """Number of enrolled students."""
        return len(self._profiles)
