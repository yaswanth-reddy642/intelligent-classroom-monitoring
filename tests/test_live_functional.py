"""Live functional test — tests every feature against the running server.

Prerequisites: Backend must be running on http://localhost:8000
"""
import sys, os, time, json
os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding='utf-8')

import requests
import numpy as np

BASE = "http://localhost:8000"
PASS = 0
FAIL = 0

def test(name):
    def wrapper(func):
        global PASS, FAIL
        try:
            func()
            print(f"  [PASS] {name}")
            PASS += 1
        except Exception as e:
            print(f"  [FAIL] {name} -- {e}")
            FAIL += 1
    return wrapper

print("=" * 65)
print("  LIVE FUNCTIONAL TEST")
print("=" * 65)

# ── 1. Health ───────────────────────────────────────────────────
print("\n[1] Health Check")

@test("GET /api/health returns 200")
def _():
    r = requests.get(f"{BASE}/api/health", timeout=5)
    assert r.status_code == 200
    d = r.json()
    assert d["status"] == "healthy"
    assert d["version"] == "1.0.0"

# ── 2. Detection Endpoints ─────────────────────────────────────
print("\n[2] Detection Endpoints")

@test("GET /api/detection/status shows not running")
def _():
    r = requests.get(f"{BASE}/api/detection/status")
    assert r.status_code == 200
    d = r.json()
    assert d["running"] == False
    assert d["fps"] == 0.0

@test("GET /api/detection/current returns empty when not running")
def _():
    r = requests.get(f"{BASE}/api/detection/current")
    assert r.status_code == 200
    d = r.json()
    assert d["running"] == False
    assert d["tracks"] == []

@test("GET /api/detection/frame returns 404 when no frame")
def _():
    r = requests.get(f"{BASE}/api/detection/frame")
    assert r.status_code == 404

# ── 3. Context / Settings ──────────────────────────────────────
print("\n[3] Context & Settings")

@test("GET /api/settings/context returns LECTURE")
def _():
    r = requests.get(f"{BASE}/api/settings/context")
    assert r.status_code == 200
    d = r.json()
    assert d["mode"] == "LECTURE"
    assert d["multiplier"] == 1.0

@test("POST /api/settings/context change to EXAM")
def _():
    r = requests.post(f"{BASE}/api/settings/context", json={"mode": "EXAM"})
    assert r.status_code == 200
    assert r.json()["mode"] == "EXAM"

@test("Verify EXAM context and multiplier 1.5")
def _():
    r = requests.get(f"{BASE}/api/settings/context")
    d = r.json()
    assert d["mode"] == "EXAM"
    assert d["multiplier"] == 1.5

@test("POST /api/settings/context change to BREAK")
def _():
    r = requests.post(f"{BASE}/api/settings/context", json={"mode": "BREAK"})
    assert r.status_code == 200

@test("Verify BREAK context and multiplier")
def _():
    r = requests.get(f"{BASE}/api/settings/context")
    d = r.json()
    assert d["mode"] == "BREAK"
    assert d["multiplier"] <= 0.5  # BREAK has low multiplier

@test("Reset to LECTURE")
def _():
    r = requests.post(f"{BASE}/api/settings/context", json={"mode": "LECTURE"})
    assert r.status_code == 200

@test("Invalid context returns 400")
def _():
    r = requests.post(f"{BASE}/api/settings/context", json={"mode": "INVALID_MODE"})
    assert r.status_code == 400

@test("GET /api/settings/model-info returns YOLO config")
def _():
    r = requests.get(f"{BASE}/api/settings/model-info")
    assert r.status_code == 200
    d = r.json()
    assert "yolo11n" in d["model_path"]
    assert d["image_size"] == 640
    assert "0" in d["target_classes"]  # class 0 = student

# ── 4. Alerts CRUD ─────────────────────────────────────────────
print("\n[4] Alerts (MongoDB CRUD)")

@test("GET /api/alerts returns list")
def _():
    r = requests.get(f"{BASE}/api/alerts")
    assert r.status_code == 200
    d = r.json()
    assert "alerts" in d
    assert "total" in d

@test("GET /api/alerts/count returns counts")
def _():
    r = requests.get(f"{BASE}/api/alerts/count")
    assert r.status_code == 200
    d = r.json()
    assert "total" in d
    assert "new" in d
    assert "acknowledged" in d
    assert "resolved" in d
    assert "today" in d

@test("GET /api/alerts with status filter")
def _():
    r = requests.get(f"{BASE}/api/alerts", params={"status": "NEW", "limit": 10})
    assert r.status_code == 200

@test("GET /api/alerts/nonexistent returns 404")
def _():
    r = requests.get(f"{BASE}/api/alerts/nonexistent_id_12345")
    assert r.status_code == 404

# ── 5. Students CRUD ───────────────────────────────────────────
print("\n[5] Students (MongoDB CRUD)")

@test("GET /api/students returns list with privacy notice")
def _():
    r = requests.get(f"{BASE}/api/students")
    assert r.status_code == 200
    d = r.json()
    assert "students" in d
    assert "privacy_notice" in d
    assert "anonymous" in d["privacy_notice"].lower()

@test("GET /api/students/privacy returns privacy notice")
def _():
    r = requests.get(f"{BASE}/api/students/privacy")
    assert r.status_code == 200
    d = r.json()
    assert "privacy_notice" in d

@test("POST /api/students creates a student record")
def _():
    r = requests.post(f"{BASE}/api/students", json={
        "name": "Test Student",
        "roll_number": "TEST-001",
        "department": "Computer Science",
        "section": "A"
    })
    assert r.status_code == 200
    d = r.json()
    assert d["student_id"].startswith("STU-")
    assert d["name"] == "Test Student"

@test("GET /api/students shows the created student")
def _():
    r = requests.get(f"{BASE}/api/students")
    d = r.json()
    found = any(s.get("roll_number") == "TEST-001" for s in d["students"])
    assert found, "Created student not found"

@test("DELETE /api/students/TEST-001 removes the student")
def _():
    r = requests.delete(f"{BASE}/api/students/TEST-001")
    assert r.status_code == 200

@test("Verify student was deleted")
def _():
    r = requests.get(f"{BASE}/api/students")
    d = r.json()
    found = any(s.get("roll_number") == "TEST-001" for s in d["students"])
    assert not found, "Student should have been deleted"

# ── 6. Dashboard Stats ─────────────────────────────────────────
print("\n[6] Dashboard Statistics")

@test("GET /api/stats/dashboard returns all fields")
def _():
    r = requests.get(f"{BASE}/api/stats/dashboard")
    assert r.status_code == 200
    d = r.json()
    required = ["pipeline_running", "fps", "total_alerts", "new_alerts",
                "today_alerts", "enrolled_students", "context"]
    for key in required:
        assert key in d, f"Missing field: {key}"

@test("GET /api/stats/live returns live stats")
def _():
    r = requests.get(f"{BASE}/api/stats/live")
    assert r.status_code == 200
    d = r.json()
    assert "running" in d
    assert "fps" in d
    assert "student_count" in d
    assert "phone_count" in d

# ── 7. WebSocket ────────────────────────────────────────────────
print("\n[7] WebSocket Connection")

@test("WebSocket /ws/live connects and receives data")
def _():
    import websockets
    import asyncio

    async def ws_test():
        async with websockets.connect("ws://localhost:8000/ws/live") as ws:
            msg = await asyncio.wait_for(ws.recv(), timeout=3)
            data = json.loads(msg)
            assert data["type"] in ("frame", "status")
            return True

    result = asyncio.run(ws_test())
    assert result

# ── 8. AI Pipeline Direct Test ──────────────────────────────────
print("\n[8] AI Pipeline Direct (no server)")

@test("Pipeline processes a blank frame end-to-end")
def _():
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from ai_pipeline.config import load_config
    from ai_pipeline.pipeline import ClassroomMonitoringPipeline
    config = load_config()
    pipeline = ClassroomMonitoringPipeline(config)
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    result = pipeline.process_frame(frame)
    assert "frame_id" in result
    assert "student_count" in result
    assert "phone_count" in result
    assert "tracks" in result
    assert "anomalies" in result
    assert "detections" in result
    assert result["frame_id"] == 1
    assert result["student_count"] == 0  # blank frame, no students
    assert result["phone_count"] == 0

@test("Pipeline context change works")
def _():
    from ai_pipeline.config import load_config
    from ai_pipeline.pipeline import ClassroomMonitoringPipeline
    config = load_config()
    pipeline = ClassroomMonitoringPipeline(config)
    assert pipeline.set_context("EXAM") == True
    ctx = pipeline.context_engine.get_context()
    assert ctx.mode.value == "EXAM"
    assert pipeline.set_context("INVALID") == False

@test("Score fusion produces correct result")
def _():
    from ai_pipeline.anomaly.fusion import ScoreFusion, FusionConfig
    f = ScoreFusion(FusionConfig(mode="weighted_average", learned_weight=0.6, context_weight=0.4))
    r = f.fuse(context_score=0.5, learned_score=0.8)
    assert abs(r.final_score - 0.68) < 0.01
    assert r.fusion_mode == "weighted_average"

    # Max mode
    f2 = ScoreFusion(FusionConfig(mode="max"))
    r2 = f2.fuse(context_score=0.3, learned_score=0.9)
    assert r2.final_score == 0.9

    # None learned → fallback to context
    r3 = f.fuse(context_score=0.7, learned_score=None)
    assert r3.final_score == 0.7
    assert r3.fusion_mode == "context_only"

# ── 9. Research Models Inference ────────────────────────────────
print("\n[9] Research Models Inference")

@test("CNN-LSTM forward pass with batch")
def _():
    import torch
    from research.models.cnn_lstm import CNNLSTM
    model = CNNLSTM(backbone_name="resnet18", pretrained=False,
                     embedding_dim=128, lstm_hidden=64, lstm_layers=1, dropout=0.1)
    model.eval()
    x = torch.randn(2, 4, 3, 224, 224)
    with torch.no_grad():
        out = model(x)
    assert out["anomaly_score"].shape == (2,)
    assert (out["anomaly_score"] >= 0).all()
    assert (out["anomaly_score"] <= 1).all()
    info = model.get_model_info()
    assert info["total_parameters"] > 0

@test("Temporal Transformer forward pass with attention")
def _():
    import torch
    from research.models.temporal_transformer import TemporalTransformer
    model = TemporalTransformer(embedding_dim=64, num_layers=2, num_heads=4,
                                 ff_dim=128, dropout=0.1)
    model.eval()
    x = torch.randn(2, 8, 64)
    with torch.no_grad():
        out = model(x)
    assert out["anomaly_score"].shape == (2,)
    assert out["attention_weights"].shape == (2, 8)
    # Attention weights should sum to ~1
    attn_sum = out["attention_weights"].sum(dim=1)
    assert (attn_sum - 1.0).abs().max() < 0.01

@test("Temporal Localization finds anomaly segments")
def _():
    from research.temporal import TemporalLocalizer
    loc = TemporalLocalizer(threshold=0.5, min_duration=0.5, fps=10)
    scores = np.array([0.1]*20 + [0.9]*30 + [0.1]*20)
    result = loc.localize(scores, fps=10)
    assert len(result.segments) >= 1
    seg = result.segments[0]
    assert seg.start_time >= 1.5
    assert seg.end_time <= 5.5
    assert seg.max_score >= 0.8

# ── 10. MongoDB Direct ──────────────────────────────────────────
print("\n[10] MongoDB Direct Verification")

@test("MongoDB collections have correct indexes")
def _():
    from pymongo import MongoClient
    client = MongoClient("mongodb://localhost:27017", serverSelectionTimeoutMS=2000)
    db = client["classroom_monitoring"]
    alert_indexes = db.alerts.index_information()
    assert any("timestamp" in idx for idx in alert_indexes)
    assert any("status" in idx for idx in alert_indexes)
    student_indexes = db.students.index_information()
    assert any("student_id" in idx for idx in student_indexes)

# ── RESULTS ─────────────────────────────────────────────────────
print()
print("=" * 65)
print(f"  LIVE FUNCTIONAL TEST: {PASS} passed, {FAIL} failed / {PASS+FAIL} total")
if FAIL == 0:
    print("  ALL FUNCTIONALITIES WORKING PROPERLY!")
else:
    print(f"  {FAIL} issue(s) need attention")
print("=" * 65)

sys.exit(1 if FAIL > 0 else 0)
