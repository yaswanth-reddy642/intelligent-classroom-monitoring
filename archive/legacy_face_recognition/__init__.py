"""Face recognition module for student identification."""
from ai_pipeline.face_recognition.models import (
    StudentProfile, FaceDetectionResult, FaceEmbedding, MatchResult, EnrollmentResult
)
from ai_pipeline.face_recognition.recognition_engine import FaceRecognitionEngine
from ai_pipeline.face_recognition.enrollment import StudentEnrollment

__all__ = [
    'StudentProfile', 'FaceDetectionResult', 'FaceEmbedding', 
    'MatchResult', 'EnrollmentResult',
    'FaceRecognitionEngine', 'StudentEnrollment',
]
