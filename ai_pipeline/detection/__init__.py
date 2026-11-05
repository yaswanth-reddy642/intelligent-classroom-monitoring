"""Object detection module using YOLOv11."""
from ai_pipeline.detection.models import Detection, DetectionResult
from ai_pipeline.detection.detector import YOLODetector

__all__ = ["Detection", "DetectionResult", "YOLODetector"]
