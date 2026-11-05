from typing import Dict, Any, List

class TrackedObject:
    def __init__(self, track_id: str, bbox, cls: str, confidence: float, first_seen: float):
        self.id = track_id
        self.bbox = bbox
        self.cls = cls
        self.confidence = confidence
        self.first_seen = first_seen
        self.last_seen = first_seen
        self.duration = 0.0
        self.state = "unknown"


class Tracker:
    def __init__(self):
        self.tracks: Dict[str, TrackedObject] = {}
        self._next_id = 1

    def update(self, detections: List[Dict[str, Any]], timestamp: float):
        # Placeholder naive tracker: assign new ID to every detection
        self.tracks = {}
        for det in detections:
            tid = f"ST-{self._next_id:03d}"
            self._next_id += 1
            to = TrackedObject(tid, det.get("bbox"), det.get("class"), det.get("score", 0.0), timestamp)
            self.tracks[tid] = to
        return list(self.tracks.values())
