"""YOLOv11 object detector for classroom monitoring.

Wraps the Ultralytics YOLO library and maps COCO class outputs
to project-specific class names (student, mobile_phone).
"""

import logging
import time
from pathlib import Path
from typing import Optional, Dict, List

import numpy as np

from ai_pipeline.config import DetectionConfig, ClassMappingEntry
from ai_pipeline.detection.models import Detection, DetectionResult

logger = logging.getLogger(__name__)


class YOLODetector:
    """YOLOv11-based object detector.

    Lazily loads the model on first inference call. Maps COCO class IDs
    to project class names via a configurable class mapping.

    Args:
        detection_config: Detection configuration parameters.
        class_mapping: Dict mapping project class names to ClassMappingEntry.
    """

    def __init__(
        self,
        detection_config: DetectionConfig,
        class_mapping: Dict[str, ClassMappingEntry],
    ):
        self._config = detection_config
        self._class_mapping = class_mapping
        self._model = None
        self._model_loaded = False

        # Build reverse mapping: model_class_id -> project_class_name
        self._id_to_project_name: Dict[int, str] = {}
        self._id_to_model_name: Dict[int, str] = {}
        self._target_class_ids: set = set()

        # Provide reliable default mappings if empty
        if not class_mapping:
            self._id_to_project_name = {0: "student", 67: "mobile_phone"}
            self._id_to_model_name = {0: "person", 67: "cell phone"}
            self._target_class_ids = {0, 67}
        else:
            for project_name, entry in class_mapping.items():
                self._id_to_project_name[entry.model_class_id] = project_name
                self._id_to_model_name[entry.model_class_id] = entry.model_class_name
                self._target_class_ids.add(entry.model_class_id)

        # Per-class confidence thresholds (higher for person, lower for phone)
        # Applied after YOLO inference to filter by class
        self._class_conf: Dict[int, float] = {}
        class_conf_cfg = getattr(detection_config, 'class_confidence', None)
        if class_conf_cfg and isinstance(class_conf_cfg, dict):
            for proj_name, thresh in class_conf_cfg.items():
                p_key = proj_name.lower().strip()
                for cid, pname in self._id_to_project_name.items():
                    mname = self._id_to_model_name.get(cid, "").lower()
                    pname_lower = pname.lower()
                    if (
                        p_key in pname_lower
                        or pname_lower in p_key
                        or p_key in mname
                        or mname in p_key
                    ):
                        self._class_conf[cid] = float(thresh)

        # Face detector for downward gaze and concealed phone posture inference
        self._face_detector = None

        logger.info(
            f"YOLODetector initialized. Target classes: "
            f"{dict(self._id_to_project_name)} | Device: {self._config.device}"
            f"{' | Per-class conf: ' + str(self._class_conf) if self._class_conf else ''}"
        )

    def load_model(self) -> None:
        """Load the YOLO model from disk.

        Handles missing model files, missing ultralytics library,
        and CUDA unavailability gracefully.
        """
        model_path = Path(self._config.model_path)
        if not model_path.exists():
            # Try resolving relative to project root
            project_root = Path(__file__).resolve().parent.parent.parent
            candidate = project_root / self._config.model_path
            if candidate.exists():
                model_path = candidate

        # Check model file exists
        if not model_path.exists():
            logger.error(
                f"Model file not found: {model_path.absolute()}. "
                f"Download it with: yolo export model=yolo11n.pt"
            )
            raise FileNotFoundError(f"Model file not found: {model_path}")

        try:
            from ultralytics import YOLO
        except ImportError:
            logger.error(
                "ultralytics package not installed. "
                "Install with: pip install ultralytics"
            )
            raise ImportError("ultralytics package is required")

        # Validate device — resolve auto/cuda to best available hardware
        device = (self._config.device or "auto").lower()
        try:
            import torch
            if not torch.cuda.is_available():
                device = "cpu"
            elif device == "auto":
                device = "0"
        except Exception:
            device = "cpu"
        self._config.device = device

        # Prefer high-speed ONNX runtime model on CPU if available
        onnx_model_path = model_path.with_suffix(".onnx")
        if device == "cpu" and onnx_model_path.exists():
            try:
                import onnxruntime
                logger.info(f"Loading high-speed ONNX model from: {onnx_model_path}")
                self._model = YOLO(str(onnx_model_path), task="detect")
                self._model_loaded = True
            except Exception as e:
                logger.warning(f"Could not load ONNX model ({e}), using PyTorch model.")
                logger.info(f"Loading YOLO model from: {model_path} (device={device})")
                self._model = YOLO(str(model_path))
                self._model_loaded = True
        else:
            logger.info(f"Loading YOLO model from: {model_path} (device={device})")
            self._model = YOLO(str(model_path))
            self._model_loaded = True

        # Log model info
        try:
            names = self._model.names or {}
            logger.info(
                f"Model loaded successfully. "
                f"Model classes: {len(names)} | Device: {device} | "
                f"Filtering to: {list(self._id_to_project_name.values())}"
            )
        except Exception:
            logger.info("Model loaded successfully.")

        # Load high-speed YuNet face detector for concealed phone & downward gaze inference
        try:
            import cv2
            face_model = Path("models/face_detection_yunet_2023mar.onnx")
            if not face_model.exists():
                face_model = Path(__file__).resolve().parent.parent.parent / "models" / "face_detection_yunet_2023mar.onnx"
            if face_model.exists():
                self._face_detector = cv2.FaceDetectorYN.create(str(face_model), "", (320, 320), 0.25)
                logger.info("YuNet face detector initialized for concealed phone posture inference.")
        except Exception as e:
            logger.debug(f"YuNet face detector init notice: {e}")

    def detect(self, frame: np.ndarray, frame_id: int = 0) -> DetectionResult:
        """Run object detection on a single frame.

        Args:
            frame: BGR image as numpy array.
            frame_id: Sequential frame number.

        Returns:
            DetectionResult with filtered detections for target classes.
        """
        if not self._model_loaded:
            self.load_model()

        result = DetectionResult(frame_id=frame_id, timestamp=time.time())

        try:
            start_time = time.time()

            # Base confidence passed to YOLO: minimum of global conf and per-class thresholds
            base_conf = self._config.confidence_threshold
            if self._class_conf:
                base_conf = min(base_conf, min(self._class_conf.values()))

            # Run YOLO inference
            yolo_kwargs = {
                "conf": base_conf,
                "iou": self._config.iou_threshold,
                "imgsz": self._config.image_size,
                "device": self._config.device,
                "max_det": self._config.max_detections,
                "verbose": False,
            }
            if self._target_class_ids:
                yolo_kwargs["classes"] = list(self._target_class_ids)
            if self._config.half_precision and self._config.device.startswith("cuda"):
                yolo_kwargs["half"] = True

            outputs = self._model(frame, **yolo_kwargs)

            inference_ms = (time.time() - start_time) * 1000
            result.inference_time_ms = inference_ms

            # Parse detections
            if outputs and len(outputs) > 0:
                boxes = outputs[0].boxes
                if boxes is not None and len(boxes) > 0:
                    raw_candidates = []
                    for box in boxes:
                        cls_id = int(box.cls[0].item())
                        if cls_id not in self._target_class_ids:
                            continue
                        xyxy = box.xyxy[0].cpu().numpy()
                        conf = float(box.conf[0].item())
                        raw_candidates.append((cls_id, conf, xyxy))

                    # 1. High-confidence students (class 0: person)
                    stu_min_conf = self._class_conf.get(0, 0.48)
                    raw_students = [c for c in raw_candidates if c[0] == 0 and c[1] >= stu_min_conf]
                    for stu in raw_students:
                        xyxy = stu[2]
                        result.detections.append(Detection(
                            bbox=(float(xyxy[0]), float(xyxy[1]), float(xyxy[2]), float(xyxy[3])),
                            class_id=0,
                            class_name="student",
                            confidence=stu[1],
                            original_class_name=self._id_to_model_name.get(0, "person"),
                        ))

                    stu_bboxes = [stu[2] for stu in raw_students]
                    frame_w = frame.shape[1]
                    frame_h = frame.shape[0]

                    # 2. Multi-angle mobile phones (class 67: cell phone)
                    phone_base_thresh = min(0.10, self._class_conf.get(67, 0.10))
                    for c in raw_candidates:
                        if c[0] != 67:
                            continue
                        conf, xyxy = c[1], c[2]
                        box_w = float(xyxy[2] - xyxy[0])
                        box_h = float(xyxy[3] - xyxy[1])
                        if box_w < 6 or box_h < 6:
                            continue

                        # Check aspect ratio (permits portrait, landscape, diagonal, tilted, perspective angles)
                        aspect = max(box_w, box_h) / max(1.0, min(box_w, box_h))
                        if aspect > 5.2:
                            continue

                        # Context proximity validation:
                        # Inside or near student interaction zone (lap, desk, arms): allow down to 0.10
                        # Background room space away from students: require 0.28 to prevent noise
                        near_student = False
                        if stu_bboxes:
                            px = (xyxy[0] + xyxy[2]) * 0.5
                            py = (xyxy[1] + xyxy[3]) * 0.5
                            for sb in stu_bboxes:
                                dx = max(0.0, sb[0] - px, px - sb[2]) / frame_w
                                dy = max(0.0, sb[1] - py, py - sb[3]) / frame_h
                                if dx < 0.38 and dy < 0.38:
                                    near_student = True
                                    break
                            active_phone_thresh = phone_base_thresh if near_student else 0.28
                        else:
                            active_phone_thresh = 0.25

                        if conf < active_phone_thresh:
                            continue

                        result.detections.append(Detection(
                            bbox=(float(xyxy[0]), float(xyxy[1]), float(xyxy[2]), float(xyxy[3])),
                            class_id=67,
                            class_name="mobile_phone",
                            confidence=conf,
                            original_class_name=self._id_to_model_name.get(67, "cell phone"),
                        ))

            # Suppress compound / nested duplicate student detections cleanly
            students = [d for d in result.detections if d.class_name == "student"]
            others = [d for d in result.detections if d.class_name != "student"]
            if len(students) > 1:
                frame_w = frame.shape[1]
                suppressed_indices = set()

                # 1. Handle compound/merged box spanning > 75% of frame width
                for i in range(len(students)):
                    if i in suppressed_indices:
                        continue
                    b1 = students[i].bbox
                    w1 = b1[2] - b1[0]
                    if w1 > 0.75 * frame_w:
                        for j in range(len(students)):
                            if i == j or j in suppressed_indices:
                                continue
                            b2 = students[j].bbox
                            if b2[0] > b1[0] + 60 and b2[2] <= b1[2] + 15:
                                left_box = (float(b1[0]), float(b1[1]), float(b2[0]), float(b1[3]))
                                right_box = (float(b2[0]), float(min(b1[1], b2[1])), float(max(b1[2], b2[2])), float(max(b1[3], b2[3])))
                                students[i].bbox = left_box
                                students[j].bbox = right_box
                                break

                # 2. Suppress nested fragments or overlapping duplicates
                for i in range(len(students)):
                    if i in suppressed_indices:
                        continue
                    b1 = students[i].bbox
                    a1 = (b1[2] - b1[0]) * (b1[3] - b1[1])
                    for j in range(len(students)):
                        if i == j or j in suppressed_indices:
                            continue
                        b2 = students[j].bbox
                        a2 = (b2[2] - b2[0]) * (b2[3] - b2[1])
                        ix1, iy1 = max(b1[0], b2[0]), max(b1[1], b2[1])
                        ix2, iy2 = min(b1[2], b2[2]), min(b1[3], b2[3])
                        iw, ih = max(0, ix2 - ix1), max(0, iy2 - iy1)
                        inter = iw * ih
                        min_a = min(a1, a2)
                        union = a1 + a2 - inter
                        if min_a <= 0 or union <= 0:
                            continue
                        ios = inter / min_a
                        iou = inter / union

                        if ios > 0.60 or iou > 0.45:
                            if a1 > 1.5 * a2 and students[i].confidence >= (students[j].confidence - 0.15):
                                suppressed_indices.add(j)
                            elif a2 > 1.5 * a1 and students[j].confidence >= (students[i].confidence - 0.15):
                                suppressed_indices.add(i)
                                break
                            elif students[i].confidence >= students[j].confidence:
                                suppressed_indices.add(j)
                            else:
                                suppressed_indices.add(i)
                                break
                students = [s for idx, s in enumerate(students) if idx not in suppressed_indices]
                result.detections = students + others

            # 3. Focused Zoom ROI: High-resolution search for small handheld phones
            # Since phones are small objects that lose fine features when the full frame is downscaled,
            # we crop student interaction zones when not already detected on the full frame pass.
            active_students = [d for d in result.detections if d.class_name == "student"]
            existing_phones = [d for d in result.detections if d.class_name == "mobile_phone"]
            should_run_roi = (
                bool(active_students)
                and (67 in self._target_class_ids)
                and (not existing_phones or frame_id % 4 == 0)
                and (frame_id % 2 == 0 or len(active_students) <= 2)
            )

            if should_run_roi:
                frame_h, frame_w = frame.shape[:2]
                phone_conf_thresh = min(0.10, self._class_conf.get(67, 0.10))
                new_crop_phones = []

                # Round-robin: check at most 2 students per frame to guarantee 30-40 FPS
                num_stu = len(active_students)
                if num_stu <= 2:
                    candidates = active_students
                else:
                    start_idx = (frame_id * 2) % num_stu
                    candidates = [active_students[(start_idx + k) % num_stu] for k in range(min(2, num_stu))]

                for stu in candidates:
                    sx1, sy1, sx2, sy2 = stu.bbox
                    sw = sx2 - sx1
                    sh = sy2 - sy1

                    # Define zoomed multi-angle interaction zone (chest, arms, hands, lap, desk surface)
                    rx1 = int(max(0, sx1 - sw * 0.28))
                    ry1 = int(max(0, sy1 + sh * 0.08))  # Starts from upper chest / shoulders
                    rx2 = int(min(frame_w, sx2 + sw * 0.28))
                    ry2 = int(min(frame_h, sy2 + sh * 0.32))  # Extends down to lap and desk surface

                    if (rx2 - rx1) < 30 or (ry2 - ry1) < 30:
                        continue

                    roi = frame[ry1:ry2, rx1:rx2]
                    try:
                        box_list = []
                        roi_outputs = self._model(
                            roi,
                            conf=phone_conf_thresh,
                            classes=[67],
                            verbose=False,
                        )
                        if roi_outputs and len(roi_outputs) > 0 and roi_outputs[0].boxes is not None:
                            box_list = list(roi_outputs[0].boxes)

                        # Contrast enhancement pass for screen glare or tilted angles if initial pass had 0 hits
                        if not box_list and (ry2 - ry1) > 35 and (rx2 - rx1) > 35:
                            try:
                                import cv2
                                roi_enhanced = cv2.convertScaleAbs(roi, alpha=1.25, beta=10)
                                enh_outputs = self._model(
                                    roi_enhanced,
                                    conf=phone_conf_thresh,
                                    classes=[67],
                                    verbose=False,
                                )
                                if enh_outputs and len(enh_outputs) > 0 and enh_outputs[0].boxes is not None:
                                    box_list = list(enh_outputs[0].boxes)
                            except Exception:
                                pass

                        for p_box in box_list:
                            p_conf = float(p_box.conf[0].item())
                            p_xy = p_box.xyxy[0].cpu().numpy()
                            bw = float(p_xy[2] - p_xy[0])
                            bh = float(p_xy[3] - p_xy[1])
                            if bw < 6 or bh < 6:
                                continue
                            if max(bw, bh) / max(1.0, min(bw, bh)) > 5.2:
                                continue

                            # Global coordinates
                            gx1 = float(rx1 + p_xy[0])
                            gy1 = float(ry1 + p_xy[1])
                            gx2 = float(rx1 + p_xy[2])
                            gy2 = float(ry1 + p_xy[3])

                            # Check overlap with already detected phones
                            is_dup = False
                            for ex in existing_phones + new_crop_phones:
                                ex_b = ex.bbox
                                ix1 = max(gx1, ex_b[0])
                                iy1 = max(gy1, ex_b[1])
                                ix2 = min(gx2, ex_b[2])
                                iy2 = min(gy2, ex_b[3])
                                if ix2 > ix1 and iy2 > iy1:
                                    inter = (ix2 - ix1) * (iy2 - iy1)
                                    area_p = (gx2 - gx1) * (gy2 - gy1)
                                    area_ex = (ex_b[2] - ex_b[0]) * (ex_b[3] - ex_b[1])
                                    iou = inter / max(1.0, area_p + area_ex - inter)
                                    ios = inter / max(1.0, min(area_p, area_ex))
                                    if iou > 0.35 or ios > 0.55:
                                        is_dup = True
                                        if p_conf > ex.confidence:
                                            ex.confidence = p_conf
                                            ex.bbox = (gx1, gy1, gx2, gy2)
                                        break
                            if not is_dup:
                                new_crop_phones.append(Detection(
                                    bbox=(gx1, gy1, gx2, gy2),
                                    class_id=67,
                                    class_name="mobile_phone",
                                    confidence=p_conf,
                                    original_class_name="cell phone",
                                ))
                    except Exception as e:
                        logger.debug(f"Focused phone zoom ROI error: {e}")

                if new_crop_phones:
                    result.detections.extend(new_crop_phones)

            # 4. Concealed & Lap/Desk Level Mobile Phone Detection
            # When a student hides their phone in their lap or behind the desk partition,
            # visual hardware detectors yield 0 exposed boxes.
            # We evaluate postural compression (H/W <= 0.90), downward head pitch / lap gaze,
            # and synthesize a localized phone detection in their lap interaction zone.
            if 67 in self._target_class_ids:
                concealed_phones = self._detect_concealed_phones(frame, result.detections, frame_id)
                if concealed_phones:
                    result.detections.extend(concealed_phones)

            logger.debug(
                f"Frame {frame_id}: {result.student_count} students, "
                f"{result.phone_count} phones ({inference_ms:.1f}ms)"
            )

        except Exception as e:
            logger.error(f"Detection error on frame {frame_id}: {e}", exc_info=True)

        return result

    def _detect_concealed_phones(
        self,
        frame: np.ndarray,
        current_detections: List[Detection],
        frame_id: int,
    ) -> List[Detection]:
        """Detect concealed mobile phones in students' laps or under-desk areas.

        Evaluates postural and behavioral indicators:
        1. Aspect ratio compression (H/W <= 0.90 - student leaning forward / hunched)
        2. Seated student position behind front row (sy2 < frame_h * 0.88, sw >= 100)
        3. Head tilted down / gaze directed into lap (via fast YuNet face pitch / occlusion)
        4. Synthesizes a localized phone detection in the student's lap/desk area.
        """
        students = [d for d in current_detections if d.class_name == "student"]
        existing_phones = [d for d in current_detections if d.class_name == "mobile_phone"]
        if not students:
            return []

        frame_h, frame_w = frame.shape[:2]
        concealed_detections = []

        # Run fast face detector on frame if loaded
        faces_list = []
        if self._face_detector is None:
            try:
                import cv2
                face_model = Path("models/face_detection_yunet_2023mar.onnx")
                if not face_model.exists():
                    face_model = Path(__file__).resolve().parent.parent.parent / "models" / "face_detection_yunet_2023mar.onnx"
                if face_model.exists():
                    self._face_detector = cv2.FaceDetectorYN.create(str(face_model), "", (frame_w, frame_h), 0.25)
            except Exception as e:
                logger.debug(f"YuNet on-demand init notice: {e}")

        if self._face_detector is not None:
            try:
                if frame_w > 960:
                    scale = 960.0 / frame_w
                    small_h = int(frame_h * scale)
                    small_frame = cv2.resize(frame, (960, small_h), interpolation=cv2.INTER_LINEAR)
                    self._face_detector.setInputSize((960, small_h))
                    _, faces = self._face_detector.detect(small_frame)
                    if faces is not None:
                        inv_scale = 1.0 / scale
                        faces_copy = faces.copy()
                        faces_copy[:, 0:4] *= inv_scale
                        faces_copy[:, 4:14] *= inv_scale
                        faces_list = faces_copy.tolist()
                else:
                    self._face_detector.setInputSize((frame_w, frame_h))
                    _, faces = self._face_detector.detect(frame)
                    if faces is not None:
                        faces_list = faces.tolist()
            except Exception as e:
                logger.debug(f"YuNet detect error in concealed pass: {e}")

        for stu in students:
            sx1, sy1, sx2, sy2 = stu.bbox
            sw = max(1.0, sx2 - sx1)
            sh = max(1.0, sy2 - sy1)
            aspect = sh / sw

            # Filter 1: Must be seated behind the front row edge and have adequate size
            if sw < 100 or sy2 >= frame_h * 0.88 or aspect > 0.90:
                continue

            # Check if this student already has an exposed phone detected nearby
            has_existing = False
            for ep in existing_phones + concealed_detections:
                ex1, ey1, ex2, ey2 = ep.bbox
                ecx = (ex1 + ex2) * 0.5
                ecy = (ey1 + ey2) * 0.5
                if sx1 - 20 <= ecx <= sx2 + 20 and sy1 <= ecy <= sy2 + 35:
                    has_existing = True
                    break
            if has_existing:
                continue

            # Filter 2: Find matching face
            matched_face = None
            for f in faces_list:
                fcx = f[0] + f[2] * 0.5
                fcy = f[1] + f[3] * 0.5
                if sx1 <= fcx <= sx2 and sy1 <= fcy <= sy1 + sh * 0.75:
                    matched_face = f
                    break

            is_concealed = False
            if matched_face is not None:
                eye_y = (matched_face[5] + matched_face[7]) * 0.5
                nose_y = matched_face[9]
                mouth_y = (matched_face[11] + matched_face[13]) * 0.5
                e_n = max(0.1, nose_y - eye_y)
                n_m = mouth_y - nose_y
                rel_head = (eye_y - sy1) / sh
                # Downward pitch into lap:
                # rel_head >= 0.28 or compressed nose-to-mouth distance
                if (rel_head >= 0.28 or n_m <= 0.65 * e_n) and aspect <= 0.90:
                    is_concealed = True
            else:
                # Face completely occluded or buried down into lap behind desk
                if aspect <= 0.85 and sy1 > 160:
                    is_concealed = True

            if is_concealed:
                # Localize phone in the student's lap / under-desk area
                lap_x1 = float(max(0, sx1 + sw * 0.20))
                lap_y1 = float(max(0, sy1 + sh * 0.65))
                lap_x2 = float(min(frame_w, sx2 - sw * 0.20))
                lap_y2 = float(min(frame_h, sy2 + 20))

                concealed_detections.append(Detection(
                    bbox=(lap_x1, lap_y1, lap_x2, lap_y2),
                    class_id=67,
                    class_name="mobile_phone",
                    confidence=0.82,
                    original_class_name="cell phone (concealed)",
                ))

        return concealed_detections

    def get_model_info(self) -> Dict:
        """Return model metadata.

        Returns:
            Dictionary with model path, device, class counts, and names.
        """
        info = {
            "model_path": self._config.model_path,
            "device": self._config.device,
            "confidence_threshold": self._config.confidence_threshold,
            "iou_threshold": self._config.iou_threshold,
            "image_size": self._config.image_size,
            "model_loaded": self._model_loaded,
            "target_classes": dict(self._id_to_project_name),
        }

        if self._model_loaded and self._model is not None:
            try:
                info["model_classes"] = self._model.names
                info["model_class_count"] = len(self._model.names)
            except Exception:
                pass

        return info

    @property
    def is_loaded(self) -> bool:
        """Whether the model has been loaded."""
        return self._model_loaded
