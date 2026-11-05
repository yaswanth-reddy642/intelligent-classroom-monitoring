"""Student enrollment module with CLI support.

Handles enrolling new students via photo upload, adding additional
face photos, and managing the enrollment database.
"""

import os
import logging
from typing import List

import cv2
import numpy as np

from ai_pipeline.config import FaceRecognitionConfig
from ai_pipeline.face_recognition.models import StudentProfile, EnrollmentResult
from ai_pipeline.face_recognition.face_encoder import FaceEncoder
from ai_pipeline.face_recognition.face_database import FaceDatabase

logger = logging.getLogger(__name__)


class StudentEnrollment:
    """Handles enrollment of new students into the face recognition system.

    Supports:
    - Enroll from photo file (admin upload — primary method)
    - Enroll from numpy image (webcam capture — optional)
    - Add additional photos to existing students
    - Remove students
    - List all enrolled students
    """

    def __init__(self, config: FaceRecognitionConfig):
        self.config = config
        self.database = FaceDatabase(config)
        self.encoder = FaceEncoder(config)

    def enroll_from_photo(
        self,
        photo_path: str,
        name: str,
        roll_number: str,
        department: str = "",
        section: str = "",
        semester: int = 0,
    ) -> EnrollmentResult:
        """Enroll a student from a photo file on disk.

        Args:
            photo_path: Path to the student's face photo.
            name: Student full name.
            roll_number: Student roll number.
            department: Department name.
            section: Section identifier.
            semester: Current semester.

        Returns:
            EnrollmentResult indicating success/failure.
        """
        if not os.path.exists(photo_path):
            return EnrollmentResult(
                success=False, message=f"Photo not found: {photo_path}"
            )

        try:
            image = cv2.imread(photo_path)
            if image is None:
                return EnrollmentResult(
                    success=False, message=f"Could not read image: {photo_path}"
                )

            return self.enroll_from_image(
                image, name, roll_number, department, section, semester
            )
        except Exception as e:
            return EnrollmentResult(success=False, message=f"Error processing image: {e}")

    def enroll_from_image(
        self,
        image: np.ndarray,
        name: str,
        roll_number: str,
        department: str = "",
        section: str = "",
        semester: int = 0,
    ) -> EnrollmentResult:
        """Enroll a student from a numpy image (webcam capture).

        Args:
            image: BGR image as numpy array.
            name: Student full name.
            roll_number: Student roll number.
            department: Department name.
            section: Section identifier.
            semester: Current semester.

        Returns:
            EnrollmentResult indicating success/failure.
        """
        try:
            # Extract face embedding
            embedding = self.encoder.encode_from_image(image)
            if not embedding:
                return EnrollmentResult(
                    success=False,
                    face_detected=False,
                    message="No suitable face detected in image. "
                    "Ensure the photo contains a clear, front-facing face.",
                )

            student_id = self.database.generate_student_id()

            # Save the enrollment photo
            photo_dir = os.path.join(self.database.photos_dir, student_id)
            os.makedirs(photo_dir, exist_ok=True)
            photo_path = os.path.join(photo_dir, "enroll_0.jpg")
            cv2.imwrite(photo_path, image)

            # Create profile and store
            profile = StudentProfile(
                student_id=student_id,
                name=name,
                roll_number=roll_number,
                department=department,
                section=section,
                semester=semester,
                face_embeddings=[embedding.embedding],
                photo_paths=[photo_path],
            )

            if self.database.add_student(profile):
                logger.info(f"Enrolled student: {name} ({roll_number}) as {student_id}")
                return EnrollmentResult(
                    success=True,
                    student_id=student_id,
                    message=f"Successfully enrolled {name} as {student_id}",
                    face_detected=True,
                    embedding_extracted=True,
                )
            else:
                return EnrollmentResult(
                    success=False, message="Failed to add student to database"
                )

        except Exception as e:
            return EnrollmentResult(success=False, message=f"Error enrolling student: {e}")

    def add_photo(self, student_id: str, photo_path: str) -> EnrollmentResult:
        """Add an additional face photo to an existing student.

        Args:
            student_id: Existing student ID (e.g. 'STU-001').
            photo_path: Path to the additional photo.

        Returns:
            EnrollmentResult indicating success/failure.
        """
        if not os.path.exists(photo_path):
            return EnrollmentResult(success=False, message="Photo not found")

        student = self.database.get_student(student_id)
        if not student:
            return EnrollmentResult(
                success=False, message=f"Student {student_id} not found"
            )

        try:
            image = cv2.imread(photo_path)
            if image is None:
                return EnrollmentResult(success=False, message="Could not read image")

            embedding = self.encoder.encode_from_image(image)
            if not embedding:
                return EnrollmentResult(
                    success=False, message="No suitable face detected in image"
                )

            # Copy photo to database
            photo_dir = os.path.join(self.database.photos_dir, student_id)
            os.makedirs(photo_dir, exist_ok=True)
            idx = len(student.photo_paths)
            new_photo_path = os.path.join(photo_dir, f"enroll_{idx}.jpg")
            cv2.imwrite(new_photo_path, image)

            if self.database.add_embedding(student_id, embedding.embedding, new_photo_path):
                return EnrollmentResult(
                    success=True,
                    student_id=student_id,
                    message=f"Added photo #{idx + 1} for {student.name}",
                )
            else:
                return EnrollmentResult(
                    success=False,
                    message="Failed to add embedding (max photos reached?)",
                )

        except Exception as e:
            return EnrollmentResult(success=False, message=f"Error adding photo: {e}")

    def remove_student(self, student_id: str) -> bool:
        """Remove a student from the enrollment database."""
        return self.database.remove_student(student_id)

    def get_all_enrolled(self) -> List[StudentProfile]:
        """Get all enrolled student profiles."""
        return self.database.get_all_students()


if __name__ == "__main__":
    import argparse
    from ai_pipeline.config import load_config, setup_logging

    parser = argparse.ArgumentParser(description="Student Enrollment CLI")
    parser.add_argument("--name", type=str, help="Student name")
    parser.add_argument("--roll", type=str, help="Roll number")
    parser.add_argument("--photo", type=str, help="Path to face photo")
    parser.add_argument("--department", type=str, default="")
    parser.add_argument("--section", type=str, default="")
    parser.add_argument("--semester", type=int, default=0)
    parser.add_argument("--add-photo", nargs=2, metavar=("STUDENT_ID", "PHOTO"),
                        help="Add photo to existing student")
    parser.add_argument("--list", action="store_true", help="List enrolled students")
    parser.add_argument("--remove", type=str, help="Student ID to remove")
    parser.add_argument("--config", type=str, default=None, help="Config file path")

    args = parser.parse_args()

    config = load_config(args.config)
    setup_logging(config.logging)
    enrollment = StudentEnrollment(config.face_recognition)

    if args.list:
        students = enrollment.get_all_enrolled()
        print(f"\nEnrolled Students: {len(students)}")
        print("-" * 60)
        for s in students:
            photos = len(s.photo_paths)
            print(f"  {s.student_id}: {s.name} ({s.roll_number}) "
                  f"[{s.department} {s.section}] - {photos} photo(s)")
    elif args.remove:
        if enrollment.remove_student(args.remove):
            print(f"Removed student {args.remove}")
        else:
            print(f"Student {args.remove} not found")
    elif args.add_photo:
        result = enrollment.add_photo(args.add_photo[0], args.add_photo[1])
        print(result.message)
    elif args.name and args.roll and args.photo:
        result = enrollment.enroll_from_photo(
            args.photo, args.name, args.roll,
            args.department, args.section, args.semester,
        )
        print(result.message)
    else:
        parser.print_help()
