"""Comprehensive end-to-end verification of the entire project.

Tests: AI pipeline imports, model loading, backend startup, MongoDB,
frontend build, research models, privacy compliance, and API endpoints.
"""

import sys, os, time, subprocess, socket, importlib
os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PASS = 0
FAIL = 0
SKIP = 0

def test(name):
    def wrapper(func):
        global PASS, FAIL, SKIP
        try:
            result = func()
            if result == "SKIP":
                print(f"  ⏭️  SKIP: {name}")
                SKIP += 1
            else:
                print(f"  ✅ PASS: {name}")
                PASS += 1
        except Exception as e:
            print(f"  ❌ FAIL: {name} — {e}")
            FAIL += 1
    return wrapper

print("=" * 65)
print("  COMPREHENSIVE PROJECT VERIFICATION")
print("=" * 65)

# ── SECTION 1: AI Pipeline ──────────────────────────────────────
print("\n▶ AI Pipeline Imports")

@test("ai_pipeline.config loads")
def _():
    from ai_pipeline.config import load_config, SystemConfig
    c = load_config()
    assert isinstance(c, SystemConfig)

@test("ai_pipeline.pipeline loads")
def _():
    from ai_pipeline.pipeline import ClassroomMonitoringPipeline

@test("ai_pipeline.cli loads")
def _():
    from ai_pipeline.cli import draw_annotations, main

@test("Detection detector loads")
def _():
    from ai_pipeline.detection.detector import YOLODetector

@test("Tracking byte_tracker loads")
def _():
    from ai_pipeline.tracking.byte_tracker import ByteTrackWrapper

@test("Association engine loads")
def _():
    from ai_pipeline.association.association_engine import StudentPhoneAssociator

@test("Temporal analyzer loads")
def _():
    from ai_pipeline.temporal.temporal_analyzer import TemporalAnalyzer

@test("Context engine loads")
def _():
    from ai_pipeline.context.context_engine import ContextEngine

@test("Anomaly scorer loads")
def _():
    from ai_pipeline.anomaly.anomaly_scorer import AnomalyScorer

@test("Score fusion loads")
def _():
    from ai_pipeline.anomaly.fusion import ScoreFusion, FusionConfig

@test("Alert engine loads")
def _():
    from ai_pipeline.alerts.alert_engine import AlertEngine

@test("Video source loads")
def _():
    from ai_pipeline.video.video_source import create_video_source

# ── SECTION 2: YOLO Model ──────────────────────────────────────
print("\n▶ YOLO Model")

@test("YOLO model file exists")
def _():
    assert os.path.exists("models/yolo11n.pt"), "models/yolo11n.pt not found"

@test("YOLO model loads and runs inference")
def _():
    from ai_pipeline.config import load_config
    from ai_pipeline.detection.detector import YOLODetector
    import numpy as np
    config = load_config()
    det = YOLODetector(config.detection, config.class_mapping)
    frame = np.zeros((640, 640, 3), dtype=np.uint8)
    result = det.detect(frame, frame_id=1)
    assert result.inference_time_ms >= 0

# ── SECTION 3: Privacy Compliance ──────────────────────────────
print("\n▶ Privacy Compliance")

@test("No face_recognition import in pipeline.py")
def _():
    with open("ai_pipeline/pipeline.py", encoding="utf-8") as f:
        src = f.read()
    assert "FaceRecognitionEngine" not in src
    assert "self._face_engine" not in src

@test("TrackedObject has no identity fields")
def _():
    import dataclasses
    from ai_pipeline.tracking.models import TrackedObject
    fields = {f.name for f in dataclasses.fields(TrackedObject)}
    forbidden = {"student_id", "student_name", "roll_number", "face_similarity", "identified"}
    overlap = fields & forbidden
    assert not overlap, f"Forbidden fields present: {overlap}"

@test("CLI has no --no-face-recognition flag")
def _():
    with open("ai_pipeline/cli.py", encoding="utf-8") as f:
        src = f.read()
    assert "--no-face-recognition" not in src

@test("CLI shows privacy banner")
def _():
    with open("ai_pipeline/cli.py", encoding="utf-8") as f:
        src = f.read()
    assert "No facial identity recognition" in src or "PRIVACY" in src

@test("Face recognition files archived")
def _():
    assert os.path.isdir("archive/legacy_face_recognition")
    assert os.path.exists("archive/legacy_face_recognition/recognition_engine.py")

# ── SECTION 4: Research Models ──────────────────────────────────
print("\n▶ Research Models")

@test("CNN-LSTM model loads and runs")
def _():
    import torch
    from research.models.cnn_lstm import CNNLSTM
    m = CNNLSTM(backbone_name="resnet18", pretrained=False, embedding_dim=128, lstm_hidden=64, lstm_layers=1, dropout=0.1)
    m.eval()
    x = torch.randn(1, 4, 3, 224, 224)
    with torch.no_grad():
        out = m(x)
    assert 0 <= out["anomaly_score"].item() <= 1

@test("Temporal Transformer loads and runs")
def _():
    import torch
    from research.models.temporal_transformer import TemporalTransformer
    m = TemporalTransformer(embedding_dim=64, num_layers=2, num_heads=4, ff_dim=128, dropout=0.1)
    m.eval()
    x = torch.randn(1, 8, 64)
    with torch.no_grad():
        out = m(x)
    assert 0 <= out["anomaly_score"].item() <= 1
    assert out["attention_weights"].shape == (1, 8)

@test("TemporalTransformerVAD end-to-end")
def _():
    import torch
    from research.models.temporal_transformer import TemporalTransformerVAD
    m = TemporalTransformerVAD(backbone_name="resnet18", pretrained=False, embedding_dim=64, num_layers=1, num_heads=4, ff_dim=128)
    m.eval()
    x = torch.randn(1, 4, 3, 224, 224)
    with torch.no_grad():
        out = m(x)
    assert 0 <= out["anomaly_score"].item() <= 1

@test("AnomalyHead loads and runs")
def _():
    import torch
    from research.models.anomaly_head import AnomalyHead
    h = AnomalyHead(feature_dim=128, dropout=0.1)
    out = h(torch.randn(4, 128))
    assert out["anomaly_score"].shape == (4,)

# ── SECTION 5: Research Framework ──────────────────────────────
print("\n▶ Research Framework")

@test("Score fusion weighted_average")
def _():
    from ai_pipeline.anomaly.fusion import ScoreFusion, FusionConfig
    f = ScoreFusion(FusionConfig(mode="weighted_average", learned_weight=0.6, context_weight=0.4))
    r = f.fuse(context_score=0.5, learned_score=0.8)
    assert abs(r.final_score - 0.68) < 0.01

@test("Temporal localization")
def _():
    import numpy as np
    from research.temporal import TemporalLocalizer
    loc = TemporalLocalizer(threshold=0.5, min_duration=0.5, fps=10)
    scores = np.array([0.1]*20 + [0.8]*20 + [0.1]*20)
    result = loc.localize(scores, fps=10)
    assert len(result.segments) >= 1

@test("Threshold calibration")
def _():
    import numpy as np
    from research.evaluation.threshold_calibration import ThresholdCalibrator
    cal = ThresholdCalibrator()
    t = cal.calibrate_f1(np.array([0.1,0.2,0.5,0.6,0.8,0.9]), np.array([0,0,0,1,1,1]))
    assert 0.0 <= t <= 1.0

@test("VAD dataset import")
def _():
    from research.datasets.vad_dataset import VADDataset
    from research.datasets.sequence_builder import SequenceBuilder
    from research.datasets.split_validator import SplitValidator

@test("Training scripts import")
def _():
    from research.training.trainer_utils import set_seed, EarlyStopping, MetricTracker

@test("Evaluation scripts import")
def _():
    from research.evaluation.evaluate_vad import VADEvaluator

@test("Experiment runners import")
def _():
    from research.experiments.run_ablation import main as abl
    from research.experiments.run_robustness import main as rob

@test("Integration adapter import")
def _():
    from research.integration.temporal_anomaly_adapter import TemporalAnomalyAdapter

@test("Error analysis import")
def _():
    from research.analysis.false_positive_analyzer import FalsePositiveAnalyzer
    from research.analysis.false_negative_analyzer import FalseNegativeAnalyzer

@test("Explainability import")
def _():
    from research.explainability.vlm_explainer import VLMExplainer
    from research.explainability.evidence_selector import EvidenceSelector

@test("Visualization import")
def _():
    from research.visualization.chart_generator import ChartGenerator

# ── SECTION 6: Backend ─────────────────────────────────────────
print("\n▶ Backend")

@test("FastAPI app imports without error")
def _():
    from backend.app.main import app
    assert app.title == "Intelligent Classroom Monitoring API"

@test("InferenceService imports")
def _():
    from backend.app.services.inference_service import InferenceService

@test("MongoDB driver imports")
def _():
    from backend.app.database.mongodb import connect_db, close_db, get_db

@test("Repositories import")
def _():
    from backend.app.database.repositories import AlertRepository, StudentRepository, EventRepository

@test("MongoDB is reachable")
def _():
    s = socket.socket()
    s.settimeout(2)
    try:
        s.connect(("localhost", 27017))
    except Exception as e:
        raise AssertionError(f"MongoDB not reachable: {e}")
    finally:
        s.close()

@test("MongoDB classroom_monitoring DB exists")
def _():
    from pymongo import MongoClient
    c = MongoClient("mongodb://localhost:27017", serverSelectionTimeoutMS=2000)
    dbs = c.list_database_names()
    assert "classroom_monitoring" in dbs

@test("API routers (detection, alerts, students, statistics, settings)")
def _():
    from backend.app.api import detection, alerts, students, statistics, settings
    assert hasattr(detection, "router")
    assert hasattr(alerts, "router")
    assert hasattr(students, "router")
    assert hasattr(statistics, "router")
    assert hasattr(settings, "router")

@test("WebSocket manager imports")
def _():
    from backend.app.websocket.manager import websocket_endpoint, broadcast_alert

# ── SECTION 7: Frontend ────────────────────────────────────────
print("\n▶ Frontend")

@test("package.json exists")
def _():
    assert os.path.exists("frontend/package.json")

@test("node_modules installed")
def _():
    assert os.path.isdir("frontend/node_modules")

@test("Vite config with proxy")
def _():
    with open("frontend/vite.config.js", encoding="utf-8") as f:
        src = f.read()
    assert "/api" in src and "localhost:8000" in src

@test("Production build exists (dist/)")
def _():
    assert os.path.isdir("frontend/dist"), "Run 'npm run build' first"

@test("Frontend API service has no face enrollment")
def _():
    with open("frontend/src/services/api.js", encoding="utf-8") as f:
        src = f.read()
    assert "enrollStudent" not in src
    assert "addStudentPhoto" not in src

@test("All page components exist")
def _():
    pages = ["Dashboard", "LiveMonitoring", "Alerts", "Students", "Enrollment",
             "EventHistory", "Analytics", "Settings", "About"]
    for p in pages:
        path = f"frontend/src/pages/{p}.jsx"
        assert os.path.exists(path), f"Missing {path}"

# ── SECTION 8: Documentation ───────────────────────────────────
print("\n▶ Documentation")

@test("README.md exists and has privacy notice")
def _():
    with open("README.md", encoding="utf-8") as f:
        src = f.read()
    assert "anonymous tracking" in src.lower()

@test("All docs exist")
def _():
    docs = ["SETUP.md", "ARCHITECTURE.md", "RESEARCH.md", "DATASET.md",
            "EXPERIMENTS.md", "PRIVACY.md", "IMPLEMENTATION_AUDIT.md", "README.md"]
    for d in docs:
        assert os.path.exists(f"docs/{d}"), f"Missing docs/{d}"

@test("Research hypotheses exist")
def _():
    assert os.path.exists("research/hypotheses.md")

@test("Research config exists")
def _():
    assert os.path.exists("configs/research_config.yaml")

# ── SECTION 9: Configuration ───────────────────────────────────
print("\n▶ Configuration")

@test("default_config.yaml has face_recognition disabled")
def _():
    import yaml
    with open("configs/default_config.yaml") as f:
        cfg = yaml.safe_load(f)
    assert cfg.get("face_recognition", {}).get("enabled") == False

@test("Results directories exist")
def _():
    dirs = ["results/detection", "results/tracking", "results/anomaly",
            "results/vad", "results/ablation", "results/robustness",
            "results/performance", "results/figures"]
    for d in dirs:
        assert os.path.isdir(d), f"Missing {d}"

# ── RESULTS ─────────────────────────────────────────────────────
print()
print("=" * 65)
total = PASS + FAIL + SKIP
print(f"  RESULTS: {PASS} passed, {FAIL} failed, {SKIP} skipped / {total} total")
if FAIL == 0:
    print("  🎉 ALL CHECKS PASSED!")
else:
    print(f"  ⚠️  {FAIL} check(s) need attention")
print("=" * 65)

sys.exit(1 if FAIL > 0 else 0)
