from typing import Dict, Any, List, Tuple
import math


def bbox_center(bbox: Tuple[int,int,int,int]) -> Tuple[float,float]:
    x1,y1,x2,y2 = bbox
    return ((x1+x2)/2.0, (y1+y2)/2.0)


class Association:
    def __init__(self):
        # Maintain associations as {student_id: {phone_id: info}}
        self.assocs = {}

    def associate(self, students: List[Dict[str,Any]], phones: List[Dict[str,Any]]) -> List[Dict[str,Any]]:
        results = []
        for s in students:
            sc = bbox_center(s["bbox"]) if s.get("bbox") else (0,0)
            best = None
            for p in phones:
                pc = bbox_center(p["bbox"]) if p.get("bbox") else (0,0)
                dist = math.hypot(sc[0]-pc[0], sc[1]-pc[1])
                # simple normalized score: smaller distance -> higher score
                score = 1.0 / (1.0 + dist)
                if best is None or score > best[0]:
                    best = (score, p)
            if best:
                score, phone = best
                results.append({"student_id": s.get("id"), "phone_id": phone.get("id"), "association_score": score})
        return results
"""Student-phone spatial and temporal association engine.

Determines which detected phones are associated with which tracked
students based on bounding box proximity, containment, and temporal
consistency across frames.
"""

import logging
import time
from typing import Dict, List, Tuple, Optional

from ai_pipeline.config import AssociationConfig
from ai_pipeline.tracking.models import TrackedObject
from ai_pipeline.association.models import StudentPhoneAssociation, AssociationResult

logger = logging.getLogger(__name__)


class StudentPhoneAssociator:
    """Associates detected phones with tracked students.

    Strategy:
    1. Calculate bounding-box center distances (normalized)
    2. Check spatial containment (phone within student bbox)
    3. Compute IoU-based proximity
    4. Maintain associations across frames (temporal consistency)
    5. Output association scores in [0, 1]
    """

    def __init__(self, config: AssociationConfig):
        self._config = config
        # Active associations: key = (student_tracking_id, phone_tracking_id)
        self._active: Dict[Tuple[int, int], StudentPhoneAssociation] = {}

    def update(
        self,
        student_tracks: List[TrackedObject],
        phone_tracks: List[TrackedObject],
        frame_width: int = 1280,
        frame_height: int = 720,
    ) -> AssociationResult:
        """Update associations with current frame's tracks using competitive 1-to-1 matching.

        Args:
            student_tracks: Currently tracked students.
            phone_tracks: Currently tracked phones.
            frame_width: Frame width for normalization.
            frame_height: Frame height for normalization.

        Returns:
            AssociationResult with current unique associations.
        """
        current_time = time.time()
        current_pairs = set()

        # Step 1: Collect candidate pairs with proximity & containment
        candidates = []
        for student in student_tracks:
            for phone in phone_tracks:
                spatial = self._calc_spatial_score(
                    student.bbox, phone.bbox, frame_width, frame_height
                )
                containment = self._calc_containment_score(student.bbox, phone.bbox)

                # Score association based on both containment and spatial proximity
                if containment > 0.05:
                    combined = 0.55 * containment + 0.45 * spatial
                elif spatial >= 0.25:
                    combined = 0.80 * spatial
                else:
                    continue

                min_threshold = self._config.min_association_score
                if combined >= min_threshold:
                    candidates.append((combined, student, phone, spatial, containment))

        # Step 2: Competitive 1-to-1 matching (highest scoring pair wins)
        # Prevents one phone from being associated to multiple surrounding students
        candidates.sort(key=lambda x: x[0], reverse=True)

        assigned_students = set()
        assigned_phones = set()

        for combined, student, phone, spatial, containment in candidates:
            if student.tracking_id in assigned_students or phone.tracking_id in assigned_phones:
                continue

            assigned_students.add(student.tracking_id)
            assigned_phones.add(phone.tracking_id)

            pair_key = (student.tracking_id, phone.tracking_id)
            current_pairs.add(pair_key)

            if pair_key in self._active:
                assoc = self._active[pair_key]
                assoc.last_seen = current_time
                assoc.frame_count += 1
                assoc.spatial_score = spatial
                assoc.containment_score = containment
                temporal_bonus = min(assoc.frame_count / max(self._config.temporal_window, 1), 1.0) * 0.12
                assoc.association_score = min(1.0, combined + temporal_bonus)
            else:
                self._active[pair_key] = StudentPhoneAssociation(
                    student_tracking_id=student.tracking_id,
                    student_display_id=student.display_id,
                    phone_tracking_id=phone.tracking_id,
                    phone_display_id=phone.display_id,
                    association_score=combined,
                    spatial_score=spatial,
                    containment_score=containment,
                    start_time=current_time,
                    last_seen=current_time,
                    frame_count=1,
                )

        # Remove stale associations not seen in this frame
        stale_keys = [k for k in self._active if k not in current_pairs]
        for k in stale_keys:
            del self._active[k]

        return AssociationResult(
            associations=list(self._active.values()),
            timestamp=current_time,
        )

    def _calc_spatial_score(
        self,
        student_bbox: Tuple[float, ...],
        phone_bbox: Tuple[float, ...],
        fw: int,
        fh: int,
    ) -> float:
        """Calculate normalized distance-based spatial score with realistic proximity bounds.

        Returns 1.0 when centers overlap, 0.0 when outside close proximity.
        """
        sx = (student_bbox[0] + student_bbox[2]) / 2
        sy = (student_bbox[1] + student_bbox[3]) / 2
        px = (phone_bbox[0] + phone_bbox[2]) / 2
        py = (phone_bbox[1] + phone_bbox[3]) / 2

        diag = max((fw ** 2 + fh ** 2) ** 0.5, 1)
        dist = ((sx - px) ** 2 + (sy - py) ** 2) ** 0.5
        norm_dist = dist / diag

        max_dist = max(self._config.max_distance, 0.28)
        if norm_dist >= max_dist:
            return 0.0

        return 1.0 - (norm_dist / max_dist)

    def _calc_containment_score(
        self,
        student_bbox: Tuple[float, ...],
        phone_bbox: Tuple[float, ...],
    ) -> float:
        """Calculate how much the phone bbox is contained within the student bbox.

        Returns 1.0 if phone is fully inside student, 0.0 if no overlap.
        """
        # Intersection
        ix1 = max(student_bbox[0], phone_bbox[0])
        iy1 = max(student_bbox[1], phone_bbox[1])
        ix2 = min(student_bbox[2], phone_bbox[2])
        iy2 = min(student_bbox[3], phone_bbox[3])

        if ix2 <= ix1 or iy2 <= iy1:
            return 0.0

        intersection = (ix2 - ix1) * (iy2 - iy1)
        phone_area = max(
            (phone_bbox[2] - phone_bbox[0]) * (phone_bbox[3] - phone_bbox[1]), 1
        )

        return min(intersection / phone_area, 1.0)

    def get_association_for_student(self, tracking_id: int) -> Optional[StudentPhoneAssociation]:
        """Get the strongest active association for a given student."""
        best = None
        for key, assoc in self._active.items():
            if key[0] == tracking_id:
                if best is None or assoc.association_score > best.association_score:
                    best = assoc
        return best

    def reset(self) -> None:
        """Clear all associations."""
        self._active.clear()
