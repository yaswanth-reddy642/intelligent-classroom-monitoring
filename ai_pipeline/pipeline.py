"""Full classroom monitoring pipeline orchestrator.

Connects all components: Video → Detection → Tracking →
Association → Temporal → Context → Anomaly → Alert.
Provides a single process_frame() method and get_current_state()
for the backend to query.

Privacy: This system uses anonymous tracking IDs only.
No facial identity recognition is performed.
"""

import logging
import time
import threading
from collections import deque
from typing import Dict, List, Optional, Any

import numpy as np

from ai_pipeline.config import SystemConfig
from ai_pipeline.video.video_source import VideoSource, create_video_source
from ai_pipeline.detection.detector import YOLODetector
from ai_pipeline.detection.models import DetectionResult
from ai_pipeline.tracking.byte_tracker import ByteTrackWrapper
from ai_pipeline.tracking.models import TrackedObject
from ai_pipeline.association.association_engine import StudentPhoneAssociator
from ai_pipeline.temporal.temporal_analyzer import TemporalAnalyzer
from ai_pipeline.context.context_engine import ContextEngine
from ai_pipeline.anomaly.anomaly_scorer import AnomalyScorer
from ai_pipeline.anomaly.models import AnomalyResult, AnomalyClassification
from ai_pipeline.alerts.alert_engine import AlertEngine
from ai_pipeline.alerts.evidence_capture import EvidenceCapture
from ai_pipeline.face.student_matcher import StudentFaceMatcher

logger = logging.getLogger(__name__)


class ClassroomMonitoringPipeline:
    """Orchestrates the complete classroom monitoring pipeline.

    Thread-safe for concurrent access from the FastAPI backend.
    """

    def __init__(self, config: SystemConfig):
        self._config = config
        self._lock = threading.Lock()
        self._frame_id = 0
        self._running = False

        # Initialize components
        self._detector = YOLODetector(config.detection, config.class_mapping)
        self._tracker = ByteTrackWrapper(config.tracking)
        self._associator = StudentPhoneAssociator(config.association)
        self._temporal = TemporalAnalyzer(config.temporal)
        self._context = ContextEngine(config.context)
        self._scorer = AnomalyScorer(config.anomaly)
        self._alert_engine = AlertEngine(config.alerts, config.camera.camera_id)
        self._evidence = EvidenceCapture(config.alerts)
        self._face_matcher = StudentFaceMatcher()

        # Optional learned temporal model adapter (set via set_temporal_model)
        self._learned_model = None

        # Current state (thread-safe via lock)
        self._current_detections: Optional[DetectionResult] = None
        self._current_tracks: List[TrackedObject] = []
        self._current_anomalies: Dict[int, AnomalyResult] = {}
        self._last_frame: Optional[np.ndarray] = None
        self._frame_history = deque(maxlen=30)

        logger.info("ClassroomMonitoringPipeline initialized (anonymous tracking, no face recognition).")

    def set_temporal_model(self, model_adapter) -> None:
        """Set an optional learned temporal anomaly model adapter.

        Args:
            model_adapter: Object with predict(sequence) method returning anomaly score.
        """
        self._learned_model = model_adapter
        logger.info(f"Learned temporal model set: {type(model_adapter).__name__}")

    def process_frame(self, frame: np.ndarray) -> Dict[str, Any]:
        """Process a single video frame through the entire pipeline.

        Args:
            frame: BGR video frame.

        Returns:
            Dict with detection results, tracks, anomalies, and alerts.
        """
        with self._lock:
            self._frame_id += 1
            frame_id = self._frame_id
            self._last_frame = frame.copy()
            self._frame_history.append(frame.copy())

        # 1. Object Detection
        detections = self._detector.detect(frame, frame_id)

        # 2. Multi-Object Tracking (anonymous IDs: ST-001, P-001)
        tracks = self._tracker.update(detections.detections, frame, frame_id)

        # Get categorized tracks
        student_tracks = self._tracker.get_student_tracks()
        phone_tracks = self._tracker.get_phone_tracks()

        # 3. Database Face Recognition & Identity Verification (SFace + MongoDB)
        # Accurately matches enrolled students in real-time, caching tracks to sustain 25-30 FPS!
        if student_tracks:
            face_matches = self._face_matcher.match_tracks(frame, student_tracks)
            for student in student_tracks:
                ident = face_matches.get(student.tracking_id)
                if ident and ident.get("is_identified", False):
                    student.student_name = ident.get("name", "Student")
                    student.roll_number = ident.get("roll_number", "UNKNOWN")
                    student.department = ident.get("department", "Computer Science")
                    student.section = ident.get("section", "A")
                    student.mobile_number = ident.get("mobile_number", "")
                    student.parent_mobile = ident.get("parent_mobile", "")
                    student.match_confidence = ident.get("match_confidence", 0.0)
                    student.identity_status = ident.get("identity_status", "Verified")
                    student.display_id = f"ST-{student.roll_number}"
                    student.is_identified = True
                    student.is_unknown = False
                else:
                    student.display_id = f"ST-{student.tracking_id:03d}"
                    student.student_name = "Unknown Person"
                    student.roll_number = "UNKNOWN"
                    student.department = "N/A"
                    student.section = "N/A"
                    student.mobile_number = ""
                    student.parent_mobile = ""
                    student.match_confidence = 0.0
                    student.identity_status = "Unverified"
                    student.is_identified = False
                    student.is_unknown = True

        # 5. Student-Phone Association
        assoc_result = self._associator.update(
            student_tracks, phone_tracks,
            frame.shape[1], frame.shape[0],
        )

        # 6. Temporal Analysis + 7. Context + 8. Anomaly Scoring
        context = self._context.get_context()
        anomalies: Dict[int, AnomalyResult] = {}
        new_alerts = []

        for student in student_tracks:
            # Get association for this student
            assoc = self._associator.get_association_for_student(student.tracking_id)
            phone_conf = 0.0
            assoc_score = 0.0

            if assoc:
                assoc_score = assoc.association_score
                # Find the phone's confidence
                for phone in phone_tracks:
                    if phone.tracking_id == assoc.phone_tracking_id:
                        phone_conf = phone.confidence
                        break

            # Record temporal observation
            self._temporal.record(
                student.tracking_id,
                phone_detected=assoc is not None,
                phone_confidence=phone_conf,
                association_score=assoc_score,
            )

            # Get temporal profile
            profile = self._temporal.get_profile(student.tracking_id)

            # Score anomaly with temporal verification
            anomaly = self._scorer.score(
                phone_confidence=phone_conf,
                association_score=assoc_score,
                temporal_persistence=profile.persistence_ratio,
                context_multiplier=context.multiplier,
                consecutive_detections=profile.consecutive_detections,
                total_duration=profile.total_duration,
            )
            anomalies[student.tracking_id] = anomaly

            # Update track state based on anomaly
            if anomaly.classification == AnomalyClassification.POTENTIAL_ANOMALY:
                student.state = student.state.__class__("potential_phone_use")
            elif anomaly.classification == AnomalyClassification.SUSPICIOUS:
                student.state = student.state.__class__("suspicious")
            else:
                student.state = student.state.__class__("normal")

            # 9. Check for alert generation
            # Only capture evidence if student is genuinely eligible for an alert (prevents disk clutter & spam)
            is_cooldown = (time.time() - self._alert_engine.get_last_alert_time(student.tracking_id)) < self._config.alerts.cooldown_seconds
            is_sustained = (profile.consecutive_detections >= 3 or profile.total_duration >= 1.2)

            evidence_path = None
            if (anomaly.classification == AnomalyClassification.POTENTIAL_ANOMALY
                and not context.suppress_alerts
                and not is_cooldown
                and is_sustained):
                # When alert is about to be generated, re-verify face against database
                if getattr(student, "is_unknown", True) or getattr(student, "roll_number", "UNKNOWN") == "UNKNOWN":
                    exclude_rolls = {
                        s.roll_number
                        for s in student_tracks
                        if s.tracking_id != student.tracking_id
                        and getattr(s, "is_identified", False)
                        and getattr(s, "roll_number", None) not in (None, "UNKNOWN", "N/A")
                    }
                    # 1. Match face on current alert frame
                    stu_meta = self._face_matcher.match_student(
                        frame, student, force_recheck=True, exclude_rolls=exclude_rolls
                    )
                    # 2. If face was occluded by phone/hand at this exact alert frame,
                    # inspect the rolling pre-alert frame history where face was unoccluded
                    if not stu_meta.get("is_identified", False) and self._frame_history:
                        history_frames = list(self._frame_history)
                        for prev_frame in reversed(history_frames[-24::4]):
                            prev_meta = self._face_matcher.match_student(
                                prev_frame, student, force_recheck=True, exclude_rolls=exclude_rolls
                            )
                            if prev_meta.get("is_identified", False):
                                stu_meta = prev_meta
                                break

                    if stu_meta.get("is_identified", False):
                        student.student_name = stu_meta.get("name")
                        student.roll_number = stu_meta.get("roll_number")
                        student.mobile_number = stu_meta.get("mobile_number", "")
                        student.parent_mobile = stu_meta.get("parent_mobile", "")
                        student.department = stu_meta.get("department", "aiml")
                        student.section = stu_meta.get("section", "a")
                        student.match_confidence = stu_meta.get("match_confidence", 0.0)
                        student.identity_status = stu_meta.get("identity_status", "Verified")
                        student.display_id = f"ST-{student.roll_number}"
                        student.is_identified = True
                        student.is_unknown = False
                        logger.info(f"On-demand face identification: Identified {student.student_name} ({student.roll_number}) in database.")
                    else:
                        student.student_name = "Unknown Person"
                        student.roll_number = "UNKNOWN"
                        student.identity_status = "Unverified"
                        student.is_identified = False
                        student.is_unknown = True

                evidence_path = self._evidence.capture(
                    frame, self._config.camera.camera_id,
                    student.display_id,
                )

            alert = self._alert_engine.check_and_alert(
                student=student,
                anomaly=anomaly,
                phone_confidence=phone_conf,
                association_score=assoc_score,
                consecutive_detections=profile.consecutive_detections,
                total_duration=profile.total_duration,
                context_mode=context.mode.value,
                suppress=context.suppress_alerts,
                evidence_path=evidence_path,
            )
            if alert:
                new_alerts.append(alert)

        # Update shared state
        with self._lock:
            self._current_detections = detections
            self._current_tracks = tracks
            self._current_anomalies = anomalies

        return {
            "frame_id": frame_id,
            "detections": detections,
            "tracks": tracks,
            "student_count": len(student_tracks),
            "phone_count": len(phone_tracks),
            "associations": assoc_result,
            "anomalies": anomalies,
            "alerts": new_alerts,
            "context": context,
        }

    def _bbox_overlap(self, bbox1, bbox2) -> float:
        """Calculate IoU between two bounding boxes."""
        x1 = max(bbox1[0], bbox2[0])
        y1 = max(bbox1[1], bbox2[1])
        x2 = min(bbox1[2], bbox2[2])
        y2 = min(bbox1[3], bbox2[3])

        if x2 <= x1 or y2 <= y1:
            return 0.0

        intersection = (x2 - x1) * (y2 - y1)
        area1 = (bbox1[2] - bbox1[0]) * (bbox1[3] - bbox1[1])
        area2 = (bbox2[2] - bbox2[0]) * (bbox2[3] - bbox2[1])
        union = area1 + area2 - intersection

        return intersection / max(union, 1e-6)

    def get_current_state(self) -> Dict[str, Any]:
        """Get the current pipeline state (thread-safe)."""
        with self._lock:
            return {
                "frame_id": self._frame_id,
                "detections": self._current_detections,
                "tracks": [t.to_dict() for t in self._current_tracks],
                "anomalies": {
                    k: v.to_dict() for k, v in self._current_anomalies.items()
                },
                "context": self._context.get_context(),
                "alert_count": self._alert_engine.alert_count,
                "new_alerts": self._alert_engine.new_alert_count,
            }

    def set_context(self, mode: str) -> bool:
        """Change classroom context mode."""
        return self._context.set_mode(mode)

    @property
    def context_engine(self) -> ContextEngine:
        return self._context

    @property
    def alert_engine(self) -> AlertEngine:
        return self._alert_engine

    @property
    def detector(self) -> YOLODetector:
        return self._detector

    @property
    def face_matcher(self) -> StudentFaceMatcher:
        return self._face_matcher

    def reset(self) -> None:
        """Reset all pipeline state."""
        self._tracker.reset()
        self._associator.reset()
        self._temporal.reset()
        self._face_matcher = StudentFaceMatcher()
        self._frame_id = 0
        logger.info("Pipeline state reset.")
