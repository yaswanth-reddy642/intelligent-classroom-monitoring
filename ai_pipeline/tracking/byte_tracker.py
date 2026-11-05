"""ByteTrack multi-object tracker wrapper.

Integrates the supervision library's ByteTrack implementation and
maintains persistent tracking IDs with identity information.
"""

import logging
import time
from typing import Dict, List, Optional

import numpy as np

from ai_pipeline.config import TrackingConfig
from ai_pipeline.detection.models import Detection
from ai_pipeline.tracking.models import TrackedObject, TrackState

logger = logging.getLogger(__name__)


class ByteTrackWrapper:
    """Wraps the supervision ByteTrack tracker with identity management.

    Maintains a mapping from ByteTrack's numeric IDs to human-readable
    display IDs (ST-001, P-001) and integrates face recognition results.

    Args:
        tracking_config: ByteTrack configuration parameters.
    """

    def __init__(self, tracking_config: TrackingConfig):
        self._config = tracking_config
        self._tracker = None
        self._tracker_initialized = False

        # State management
        self._tracks: Dict[int, TrackedObject] = {}
        self._student_counter: int = 0
        self._phone_counter: int = 0
        self._id_mapping: Dict[int, str] = {}  # ByteTrack ID -> display ID

        self._initialize_tracker()

    def _initialize_tracker(self) -> None:
        """Initialize the ByteTrack tracker from supervision."""
        try:
            import supervision as sv

            self._tracker = sv.ByteTrack(
                track_activation_threshold=self._config.track_thresh,
                lost_track_buffer=self._config.track_buffer,
                minimum_matching_threshold=self._config.match_thresh,
                frame_rate=self._config.frame_rate,
            )
            # Ensure det_thresh permits sensitive multi-angle phones to activate tracks immediately
            if hasattr(self._tracker, 'det_thresh'):
                self._tracker.det_thresh = max(0.06, float(self._config.track_thresh))
            self._tracker_initialized = True
            logger.info(
                f"ByteTrack initialized: thresh={self._config.track_thresh}, "
                f"buffer={self._config.track_buffer}, "
                f"match={self._config.match_thresh}"
            )
        except ImportError:
            logger.error(
                "supervision package not installed. "
                "Install with: pip install supervision"
            )
            self._tracker_initialized = False

    def update(
        self,
        detections: List[Detection],
        frame: np.ndarray,
        frame_id: int = 0,
    ) -> List[TrackedObject]:
        """Update tracks with new detections.

        Args:
            detections: List of detections from the current frame.
            frame: Current video frame (for reference).
            frame_id: Frame sequence number.

        Returns:
            List of currently active TrackedObject instances.
        """
        if not self._tracker_initialized or self._tracker is None:
            logger.warning("ByteTrack not initialized. Returning empty tracks.")
            return []

        if not detections:
            # Still update tracker with empty detections to age out lost tracks
            try:
                import supervision as sv
                empty = sv.Detections.empty()
                self._tracker.update_with_detections(empty)
            except Exception:
                pass
            return self._get_active_tracks()

        try:
            import supervision as sv

            # Build supervision Detections from our Detection objects
            xyxy = np.array([d.bbox for d in detections], dtype=np.float32)
            confidence = np.array([d.confidence for d in detections], dtype=np.float32)
            class_ids = np.array([d.class_id for d in detections], dtype=int)

            sv_detections = sv.Detections(
                xyxy=xyxy,
                confidence=confidence,
                class_id=class_ids,
            )

            # Run ByteTrack update
            tracked = self._tracker.update_with_detections(sv_detections)

            current_time = time.time()
            active_tracker_ids = set()

            if tracked.tracker_id is not None and len(tracked.tracker_id) > 0:
                for i in range(len(tracked.tracker_id)):
                    tracker_id = int(tracked.tracker_id[i])
                    active_tracker_ids.add(tracker_id)

                    bbox = tuple(tracked.xyxy[i].tolist())
                    conf = float(tracked.confidence[i]) if tracked.confidence is not None else 0.0
                    cls_id = int(tracked.class_id[i]) if tracked.class_id is not None else 0

                    # Determine class name from original detections
                    class_name = "student"  # default
                    is_con = False
                    for det in detections:
                        if det.class_id == cls_id:
                            class_name = det.class_name
                            if getattr(det, "is_concealed", False) or getattr(det, "original_class_name", "") == "cell phone (concealed)":
                                is_con = True
                            break

                    if tracker_id in self._tracks:
                        # Update existing track
                        track = self._tracks[tracker_id]
                        track.bbox = bbox
                        track.confidence = conf
                        track.last_seen = current_time
                        track.state = TrackState.ACTIVE
                        if is_con:
                            track.is_concealed = True
                    else:
                        # Create new track
                        display_id = self._generate_display_id(class_name)
                        self._id_mapping[tracker_id] = display_id

                        track = TrackedObject(
                            tracking_id=tracker_id,
                            display_id=display_id,
                            bbox=bbox,
                            confidence=conf,
                            class_name=class_name,
                            first_seen=current_time,
                            last_seen=current_time,
                            state=TrackState.ACTIVE,
                            is_concealed=is_con,
                        )
                        self._tracks[tracker_id] = track

            # Direct Tracking Guarantee for Handheld Mobile Phones:
            # Phones move rapidly and tilt at varied angles where standard Kalman filters
            # can lag or require multiple confirmation frames.
            # Match any detected phone not yet assigned to an active track.
            active_phone_tracks = [
                self._tracks[tid] for tid in active_tracker_ids
                if tid in self._tracks and self._tracks[tid].class_name == "mobile_phone"
            ]
            for det in detections:
                if det.class_name != "mobile_phone":
                    continue
                # Check if this detection is already covered by an active track
                db = det.bbox
                dc = ((db[0] + db[2]) * 0.5, (db[1] + db[3]) * 0.5)
                matched = False
                for at in active_phone_tracks:
                    ab = at.bbox
                    ac = ((ab[0] + ab[2]) * 0.5, (ab[1] + ab[3]) * 0.5)
                    dist = ((dc[0] - ac[0]) ** 2 + (dc[1] - ac[1]) ** 2) ** 0.5
                    if dist < 45:  # Same phone position
                        matched = True
                        break
                if matched:
                    continue

                # Try associating with existing recently lost phone track within reasonable reach
                best_track = None
                best_dist = 180.0
                for tid, track in self._tracks.items():
                    if track.class_name == "mobile_phone" and tid not in active_tracker_ids:
                        tb = track.bbox
                        tc = ((tb[0] + tb[2]) * 0.5, (tb[1] + tb[3]) * 0.5)
                        dist = ((dc[0] - tc[0]) ** 2 + (dc[1] - tc[1]) ** 2) ** 0.5
                        if dist < best_dist and (current_time - track.last_seen) < 2.5:
                            best_dist = dist
                            best_track = track

                if best_track is not None:
                    best_track.bbox = tuple(db)
                    best_track.confidence = det.confidence
                    best_track.last_seen = current_time
                    best_track.state = TrackState.ACTIVE
                    if getattr(det, "is_concealed", False) or getattr(det, "original_class_name", "") == "cell phone (concealed)":
                        best_track.is_concealed = True
                    active_tracker_ids.add(best_track.tracking_id)
                else:
                    # Allocate new phone track immediately so live monitoring never drops the phone
                    self._phone_counter += 1
                    new_tid = 1000 + self._phone_counter
                    display_id = f"P-{self._phone_counter:03d}"
                    self._id_mapping[new_tid] = display_id
                    is_con = getattr(det, "is_concealed", False) or getattr(det, "original_class_name", "") == "cell phone (concealed)"
                    new_track = TrackedObject(
                        tracking_id=new_tid,
                        display_id=display_id,
                        bbox=tuple(db),
                        confidence=det.confidence,
                        class_name="mobile_phone",
                        first_seen=current_time,
                        last_seen=current_time,
                        state=TrackState.ACTIVE,
                        is_concealed=is_con,
                    )
                    self._tracks[new_tid] = new_track
                    active_tracker_ids.add(new_tid)

            # Mark tracks not in current frame as lost
            for tid, track in self._tracks.items():
                if tid not in active_tracker_ids and track.state == TrackState.ACTIVE:
                    track.state = TrackState.LOST

            return self._get_active_tracks()

        except Exception as e:
            logger.error(f"Tracking update error on frame {frame_id}: {e}", exc_info=True)
            return self._get_active_tracks()

    def _generate_display_id(self, class_name: str) -> str:
        """Generate a human-readable display ID.

        Args:
            class_name: Object class ('student' or 'mobile_phone').

        Returns:
            Formatted ID like 'ST-001' or 'P-001'.
        """
        if class_name == "student":
            self._student_counter += 1
            return f"ST-{self._student_counter:03d}"
        elif class_name == "mobile_phone":
            self._phone_counter += 1
            return f"P-{self._phone_counter:03d}"
        else:
            self._student_counter += 1
            return f"OBJ-{self._student_counter:03d}"

    def _get_active_tracks(self) -> List[TrackedObject]:
        """Return list of currently active tracks."""
        return [
            t for t in self._tracks.values()
            if t.state in (TrackState.ACTIVE, TrackState.POTENTIAL_PHONE_USE,
                           TrackState.NORMAL, TrackState.SUSPICIOUS)
        ]

    def get_active_tracks(self) -> List[TrackedObject]:
        """Public method to get all active tracked objects."""
        return self._get_active_tracks()

    def get_student_tracks(self) -> List[TrackedObject]:
        """Get only student tracks that are currently active."""
        return [t for t in self._get_active_tracks() if t.class_name == "student"]

    def get_phone_tracks(self) -> List[TrackedObject]:
        """Get only phone tracks that are currently active."""
        return [t for t in self._get_active_tracks() if t.class_name == "mobile_phone"]

    def get_track_by_id(self, tracking_id: int) -> Optional[TrackedObject]:
        """Get a specific track by ByteTrack ID."""
        return self._tracks.get(tracking_id)

    def get_track_by_display_id(self, display_id: str) -> Optional[TrackedObject]:
        """Get a specific track by display ID."""
        for track in self._tracks.values():
            if track.display_id == display_id:
                return track
        return None

    @property
    def total_tracks(self) -> int:
        """Total number of tracks created since start."""
        return len(self._tracks)

    @property
    def active_count(self) -> int:
        """Number of currently active tracks."""
        return len(self._get_active_tracks())

    def reset(self) -> None:
        """Clear all tracking state and reinitialize."""
        self._tracks.clear()
        self._id_mapping.clear()
        self._student_counter = 0
        self._phone_counter = 0
        self._initialize_tracker()
        logger.info("Tracking state reset.")
