"""Configuration management for the Intelligent Classroom Monitoring system.

Loads configuration from YAML files with environment variable overrides.
All system parameters are centralized here — no hardcoded thresholds elsewhere.
"""

import os
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, Tuple

import yaml

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "configs" / "default_config.yaml"


# ============================================================
# Configuration Dataclasses
# ============================================================

@dataclass
class VideoConfig:
    """Video input configuration."""
    source_type: str = "webcam"
    source_path: str = "0"
    inference_resolution: Tuple[int, int] = (640, 640)
    display_resolution: Tuple[int, int] = (1280, 720)
    frame_skip: int = 0
    max_fps: int = 30


@dataclass
class DetectionConfig:
    """YOLOv11 object detection configuration."""
    model_path: str = "models/yolo11n.pt"
    confidence_threshold: float = 0.35
    iou_threshold: float = 0.45
    image_size: int = 640
    device: str = "auto"
    max_detections: int = 100
    half_precision: bool = False
    class_confidence: Dict[str, float] = field(default_factory=dict)  # per-class thresholds


@dataclass
class ClassMappingEntry:
    """Maps a model output class to a project class name."""
    model_class_id: int
    model_class_name: str


@dataclass
class FaceRecognitionConfig:
    """Face recognition configuration (DEPRECATED — disabled for privacy).

    This system uses anonymous tracking IDs only.
    Face recognition is archived and not used in the active pipeline.
    """
    enabled: bool = False
    model_name: str = "buffalo_l"
    similarity_threshold: float = 0.6
    max_faces_per_student: int = 5
    embedding_dimension: int = 512
    face_database_path: str = "data/face_database"
    min_face_size: int = 30
    detection_threshold: float = 0.5


@dataclass
class TrackingConfig:
    """ByteTrack multi-object tracking configuration."""
    track_thresh: float = 0.25
    track_buffer: int = 30
    match_thresh: float = 0.8
    frame_rate: int = 30


@dataclass
class AssociationConfig:
    """Student-phone association configuration."""
    max_distance: float = 0.3
    iou_threshold: float = 0.1
    temporal_window: int = 10
    min_association_score: float = 0.3


@dataclass
class TemporalConfig:
    """Temporal behavior analysis configuration."""
    min_phone_duration: float = 3.0
    temporal_window: float = 30.0
    min_consecutive_detections: int = 5
    persistence_threshold: float = 0.6


@dataclass
class ContextConfig:
    """Classroom context configuration."""
    default_mode: str = "LECTURE"
    mode_multipliers: Dict[str, float] = field(default_factory=lambda: {
        "LECTURE": 1.0,
        "EXAM": 1.5,
        "AUTHORIZED_PHONE_ACTIVITY": 0.1,
        "BREAK": 0.2,
    })


@dataclass
class AnomalyWeights:
    """Weights for anomaly scoring formula: A = w1*D + w2*S + w3*T + w4*C."""
    phone_detection: float = 0.25
    association: float = 0.25
    temporal_persistence: float = 0.30
    context: float = 0.20


@dataclass
class AnomalyThresholds:
    """Thresholds for anomaly classification."""
    suspicious: float = 0.4
    anomaly: float = 0.7


@dataclass
class AnomalyConfig:
    """Anomaly scoring configuration."""
    weights: AnomalyWeights = field(default_factory=AnomalyWeights)
    thresholds: AnomalyThresholds = field(default_factory=AnomalyThresholds)


@dataclass
class AlertConfig:
    """Alert engine configuration."""
    cooldown_seconds: int = 60
    evidence_capture: bool = True
    evidence_path: str = "evidence"
    evidence_retention_days: int = 30


@dataclass
class CameraConfig:
    """Camera identification configuration."""
    camera_id: str = "CAM-01"


@dataclass
class DatabaseConfig:
    """MongoDB database configuration."""
    mongodb_uri: str = "mongodb://localhost:27017"
    database_name: str = "classroom_monitoring"


@dataclass
class ServerConfig:
    """Backend server configuration."""
    host: str = "0.0.0.0"
    port: int = 8000
    frontend_url: str = "http://localhost:5173"


@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str = "INFO"
    log_file: str = "logs/classroom_monitoring.log"
    console: bool = True


@dataclass
class SystemConfig:
    """Master configuration container holding all subsystem configs."""
    video: VideoConfig = field(default_factory=VideoConfig)
    detection: DetectionConfig = field(default_factory=DetectionConfig)
    class_mapping: Dict[str, ClassMappingEntry] = field(default_factory=dict)
    face_recognition: FaceRecognitionConfig = field(default_factory=FaceRecognitionConfig)
    tracking: TrackingConfig = field(default_factory=TrackingConfig)
    association: AssociationConfig = field(default_factory=AssociationConfig)
    temporal: TemporalConfig = field(default_factory=TemporalConfig)
    context: ContextConfig = field(default_factory=ContextConfig)
    anomaly: AnomalyConfig = field(default_factory=AnomalyConfig)
    alerts: AlertConfig = field(default_factory=AlertConfig)
    camera: CameraConfig = field(default_factory=CameraConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    server: ServerConfig = field(default_factory=ServerConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)


# ============================================================
# Device Resolution
# ============================================================

def _resolve_device(device_str: str) -> str:
    """Resolve 'auto' device to the best available hardware.

    Args:
        device_str: Device string — 'auto', 'cpu', 'cuda', or 'cuda:N'.

    Returns:
        Resolved device string.
    """
    if device_str == "auto":
        try:
            import torch
            if torch.cuda.is_available():
                device = "cuda"
                logger.info(f"CUDA available. Using GPU: {torch.cuda.get_device_name(0)}")
            else:
                device = "cpu"
                logger.info("CUDA not available. Using CPU for inference.")
        except ImportError:
            device = "cpu"
            logger.warning("PyTorch not found. Defaulting to CPU.")
        return device
    return device_str


# ============================================================
# Configuration Loading
# ============================================================

def load_config(config_path: Optional[str] = None, env_override: bool = True) -> SystemConfig:
    """Load system configuration from YAML file with optional environment overrides.

    Args:
        config_path: Path to YAML config file. Uses default if None.
        env_override: Whether to apply environment variable overrides.

    Returns:
        Fully populated and validated SystemConfig.
    """
    path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH

    if path.exists():
        logger.info(f"Loading configuration from: {path}")
        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
    else:
        logger.warning(f"Config file not found: {path}. Using defaults.")
        raw = {}

    config = SystemConfig()

    # --- Video ---
    if "video" in raw:
        v = raw["video"]
        config.video = VideoConfig(
            source_type=v.get("source_type", "webcam"),
            source_path=str(v.get("source_path", "0")),
            inference_resolution=tuple(v.get("inference_resolution", [640, 640])),
            display_resolution=tuple(v.get("display_resolution", [1280, 720])),
            frame_skip=v.get("frame_skip", 0),
            max_fps=v.get("max_fps", 30),
        )

    # --- Detection ---
    if "detection" in raw:
        d = raw["detection"]
        config.detection = DetectionConfig(
            model_path=d.get("model_path", "models/yolo11n.pt"),
            confidence_threshold=d.get("confidence_threshold", 0.35),
            iou_threshold=d.get("iou_threshold", 0.45),
            image_size=d.get("image_size", 640),
            device=d.get("device", "auto"),
            max_detections=d.get("max_detections", 100),
            half_precision=d.get("half_precision", False),
            class_confidence=d.get("class_confidence", {}),
        )

    # --- Class Mapping ---
    if "class_mapping" in raw:
        for name, mapping in raw["class_mapping"].items():
            config.class_mapping[name] = ClassMappingEntry(
                model_class_id=mapping["model_class_id"],
                model_class_name=mapping["model_class_name"],
            )

    # --- Face Recognition ---
    if "face_recognition" in raw:
        fr = raw["face_recognition"]
        config.face_recognition = FaceRecognitionConfig(
            enabled=fr.get("enabled", True),
            model_name=fr.get("model_name", "buffalo_l"),
            similarity_threshold=fr.get("similarity_threshold", 0.6),
            max_faces_per_student=fr.get("max_faces_per_student", 5),
            embedding_dimension=fr.get("embedding_dimension", 512),
            face_database_path=fr.get("face_database_path", "data/face_database"),
            min_face_size=fr.get("min_face_size", 30),
            detection_threshold=fr.get("detection_threshold", 0.5),
        )

    # --- Tracking ---
    if "tracking" in raw:
        t = raw["tracking"]
        config.tracking = TrackingConfig(
            track_thresh=t.get("track_thresh", 0.25),
            track_buffer=t.get("track_buffer", 30),
            match_thresh=t.get("match_thresh", 0.8),
            frame_rate=t.get("frame_rate", 30),
        )

    # --- Association ---
    if "association" in raw:
        a = raw["association"]
        config.association = AssociationConfig(
            max_distance=a.get("max_distance", 0.3),
            iou_threshold=a.get("iou_threshold", 0.1),
            temporal_window=a.get("temporal_window", 10),
            min_association_score=a.get("min_association_score", 0.3),
        )

    # --- Temporal ---
    if "temporal" in raw:
        t = raw["temporal"]
        config.temporal = TemporalConfig(
            min_phone_duration=t.get("min_phone_duration", 3.0),
            temporal_window=t.get("temporal_window", 30.0),
            min_consecutive_detections=t.get("min_consecutive_detections", 5),
            persistence_threshold=t.get("persistence_threshold", 0.6),
        )

    # --- Context ---
    if "context" in raw:
        c = raw["context"]
        config.context = ContextConfig(
            default_mode=c.get("default_mode", "LECTURE"),
            mode_multipliers=c.get("mode_multipliers", ContextConfig().mode_multipliers),
        )

    # --- Anomaly ---
    if "anomaly" in raw:
        a = raw["anomaly"]
        weights = a.get("weights", {})
        thresholds = a.get("thresholds", {})
        config.anomaly = AnomalyConfig(
            weights=AnomalyWeights(
                phone_detection=weights.get("phone_detection", 0.25),
                association=weights.get("association", 0.25),
                temporal_persistence=weights.get("temporal_persistence", 0.30),
                context=weights.get("context", 0.20),
            ),
            thresholds=AnomalyThresholds(
                suspicious=thresholds.get("suspicious", 0.4),
                anomaly=thresholds.get("anomaly", 0.7),
            ),
        )

    # --- Alerts ---
    if "alerts" in raw:
        al = raw["alerts"]
        config.alerts = AlertConfig(
            cooldown_seconds=al.get("cooldown_seconds", 60),
            evidence_capture=al.get("evidence_capture", True),
            evidence_path=al.get("evidence_path", "evidence"),
            evidence_retention_days=al.get("evidence_retention_days", 30),
        )

    # --- Camera ---
    if "camera" in raw:
        config.camera = CameraConfig(camera_id=raw["camera"].get("camera_id", "CAM-01"))

    # --- Database ---
    if "database" in raw:
        db = raw["database"]
        config.database = DatabaseConfig(
            mongodb_uri=db.get("mongodb_uri", "mongodb://localhost:27017"),
            database_name=db.get("database_name", "classroom_monitoring"),
        )

    # --- Server ---
    if "server" in raw:
        s = raw["server"]
        config.server = ServerConfig(
            host=s.get("host", "0.0.0.0"),
            port=s.get("port", 8000),
            frontend_url=s.get("frontend_url", "http://localhost:5173"),
        )

    # --- Logging ---
    if "logging" in raw:
        lg = raw["logging"]
        config.logging = LoggingConfig(
            level=lg.get("level", "INFO"),
            log_file=lg.get("log_file", "logs/classroom_monitoring.log"),
            console=lg.get("console", True),
        )

    # Apply environment variable overrides
    if env_override:
        config = _apply_env_overrides(config)

    # Resolve auto device
    config.detection.device = _resolve_device(config.detection.device)

    return config


def _apply_env_overrides(config: SystemConfig) -> SystemConfig:
    """Apply environment variable overrides to configuration."""
    env_map = {
        "MONGODB_URI": lambda v: setattr(config.database, "mongodb_uri", v),
        "MONGODB_DATABASE": lambda v: setattr(config.database, "database_name", v),
        "MODEL_PATH": lambda v: setattr(config.detection, "model_path", v),
        "DEVICE": lambda v: setattr(config.detection, "device", v),
        "CONFIDENCE_THRESHOLD": lambda v: setattr(config.detection, "confidence_threshold", float(v)),
        "IOU_THRESHOLD": lambda v: setattr(config.detection, "iou_threshold", float(v)),
        "IMAGE_SIZE": lambda v: setattr(config.detection, "image_size", int(v)),
        "FACE_RECOGNITION_ENABLED": lambda v: setattr(config.face_recognition, "enabled", v.lower() == "true"),
        "FACE_SIMILARITY_THRESHOLD": lambda v: setattr(config.face_recognition, "similarity_threshold", float(v)),
        "CAMERA_ID": lambda v: setattr(config.camera, "camera_id", v),
        "VIDEO_SOURCE": lambda v: setattr(config.video, "source_type", v),
        "BACKEND_HOST": lambda v: setattr(config.server, "host", v),
        "BACKEND_PORT": lambda v: setattr(config.server, "port", int(v)),
        "FRONTEND_URL": lambda v: setattr(config.server, "frontend_url", v),
        "LOG_LEVEL": lambda v: setattr(config.logging, "level", v),
    }

    for env_key, setter in env_map.items():
        value = os.environ.get(env_key)
        if value is not None:
            try:
                setter(value)
                logger.debug(f"Environment override applied: {env_key}")
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid environment override {env_key}={value}: {e}")

    return config


def setup_logging(config: LoggingConfig) -> None:
    """Configure structured logging based on configuration.

    Args:
        config: Logging configuration dataclass.
    """
    log_level = getattr(logging, config.level.upper(), logging.INFO)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # Console handler
    if config.console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # File handler
    if config.log_file:
        log_path = Path(config.log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    logger.info(f"Logging configured: level={config.level}, file={config.log_file}")
