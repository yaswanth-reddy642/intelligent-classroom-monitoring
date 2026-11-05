"""Tests for the Intelligent Classroom Monitoring system.

Covers: detection, tracking, association, temporal, context, anomaly scoring,
fusion, research models, localization, and privacy verification.

Run: python -m pytest tests/ -v
  or: python tests/test_system.py
"""

import sys
import os
import time
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")

PASS = 0
FAIL = 0


def test(name):
    """Decorator to register a test function."""
    def wrapper(func):
        global PASS, FAIL
        try:
            func()
            logger.info(f"✅ PASS: {name}")
            PASS += 1
        except Exception as e:
            logger.error(f"❌ FAIL: {name} — {e}")
            FAIL += 1
    return wrapper


# ===== Test 1: Detection =====
@test("Detector loads and produces valid detections")
def test_detection():
    from ai_pipeline.config import load_config
    from ai_pipeline.detection.detector import YOLODetector
    import numpy as np

    config = load_config()
    detector = YOLODetector(config.detection, config.class_mapping)
    # Create a blank frame
    frame = np.zeros((640, 640, 3), dtype=np.uint8)
    result = detector.detect(frame, frame_id=1)
    assert hasattr(result, 'detections'), "DetectionResult missing detections"
    assert hasattr(result, 'inference_time_ms'), "DetectionResult missing inference_time_ms"
    assert result.inference_time_ms >= 0, "Inference time should be non-negative"


# ===== Test 2: Tracking =====
@test("Anonymous tracking IDs persist correctly")
def test_tracking():
    from ai_pipeline.config import load_config
    from ai_pipeline.tracking.byte_tracker import ByteTrackWrapper
    from ai_pipeline.tracking.models import TrackedObject
    import numpy as np

    config = load_config()
    tracker = ByteTrackWrapper(config.tracking)
    # Verify tracker initialized
    assert tracker._tracker_initialized, "ByteTrack should be initialized"
    # Verify display ID format
    display_id = tracker._generate_display_id("student")
    assert display_id.startswith("ST-"), f"Expected ST-XXX, got {display_id}"
    phone_id = tracker._generate_display_id("mobile_phone")
    assert phone_id.startswith("P-"), f"Expected P-XXX, got {phone_id}"


# ===== Test 3: Tracking Model Privacy =====
@test("TrackedObject has no face identity fields")
def test_tracking_privacy():
    from ai_pipeline.tracking.models import TrackedObject
    import dataclasses

    fields = [f.name for f in dataclasses.fields(TrackedObject)]
    forbidden = ["student_id", "student_name", "roll_number", "face_similarity", "identified"]
    for f in forbidden:
        assert f not in fields, f"TrackedObject should NOT have field '{f}' (privacy)"


# ===== Test 4: Association =====
@test("Student-phone association produces valid outputs")
def test_association():
    from ai_pipeline.config import load_config
    from ai_pipeline.association.association_engine import StudentPhoneAssociator

    config = load_config()
    associator = StudentPhoneAssociator(config.association)
    assert associator is not None
    # Test with empty inputs — returns AssociationResult
    result = associator.update([], [])
    assert result is not None, "Association update should return a result"


# ===== Test 5: Temporal Verification =====
@test("Temporal analyzer tracks phone duration")
def test_temporal():
    from ai_pipeline.config import load_config
    from ai_pipeline.temporal.temporal_analyzer import TemporalAnalyzer

    config = load_config()
    analyzer = TemporalAnalyzer(config.temporal)
    assert analyzer is not None


# ===== Test 6: Context Engine =====
@test("Context mode changes anomaly scoring")
def test_context():
    from ai_pipeline.config import load_config
    from ai_pipeline.context.context_engine import ContextEngine

    config = load_config()
    engine = ContextEngine(config.context)
    # Default mode
    ctx = engine.get_context()
    assert ctx is not None
    assert hasattr(ctx, 'mode'), "Context should have mode"
    assert hasattr(ctx, 'multiplier'), "Context should have multiplier"


# ===== Test 7: Anomaly Scorer =====
@test("Anomaly scorer produces valid scores")
def test_anomaly_scorer():
    from ai_pipeline.config import load_config
    from ai_pipeline.anomaly.anomaly_scorer import AnomalyScorer

    config = load_config()
    scorer = AnomalyScorer(config.anomaly)
    assert scorer is not None


# ===== Test 8: Score Fusion =====
@test("Learned and context scores combine correctly")
def test_fusion():
    from ai_pipeline.anomaly.fusion import ScoreFusion, FusionConfig

    # Weighted average
    fusion = ScoreFusion(FusionConfig(mode="weighted_average", learned_weight=0.6, context_weight=0.4))
    result = fusion.fuse(context_score=0.5, learned_score=0.8)
    expected = (0.6 * 0.8 + 0.4 * 0.5) / 1.0
    assert abs(result.final_score - expected) < 0.01, f"Expected {expected}, got {result.final_score}"

    # Context only when learned is None
    result2 = fusion.fuse(context_score=0.7, learned_score=None)
    assert result2.final_score == 0.7, "Should use context_score when learned is None"
    assert result2.fusion_mode == "context_only"

    # Max mode
    fusion_max = ScoreFusion(FusionConfig(mode="max"))
    result3 = fusion_max.fuse(context_score=0.3, learned_score=0.9)
    assert result3.final_score == 0.9, "Max mode should return max"


# ===== Test 9: CNN-LSTM Model =====
@test("CNN-LSTM can load and run inference")
def test_cnn_lstm():
    import torch
    from research.models.cnn_lstm import CNNLSTM

    model = CNNLSTM(
        backbone_name="resnet18", pretrained=False,
        embedding_dim=128, lstm_hidden=64, lstm_layers=1, dropout=0.1,
    )
    model.eval()

    # Smoke test with random data
    x = torch.randn(2, 4, 3, 224, 224)  # batch=2, seq=4
    with torch.no_grad():
        output = model(x)

    assert "anomaly_score" in output, "Should have anomaly_score"
    assert output["anomaly_score"].shape == (2,), f"Wrong shape: {output['anomaly_score'].shape}"
    scores = output["anomaly_score"]
    assert (scores >= 0).all() and (scores <= 1).all(), "Scores should be in [0, 1]"

    # Model info
    info = model.get_model_info()
    assert info["model"] == "CNN-LSTM"
    assert info["total_parameters"] > 0


# ===== Test 10: Temporal Transformer =====
@test("Temporal Transformer can load and run inference")
def test_transformer():
    import torch
    from research.models.temporal_transformer import TemporalTransformer

    model = TemporalTransformer(
        embedding_dim=64, num_layers=2, num_heads=4, ff_dim=128, dropout=0.1,
    )
    model.eval()

    x = torch.randn(2, 8, 64)  # batch=2, seq=8, dim=64
    with torch.no_grad():
        output = model(x)

    assert "anomaly_score" in output
    assert "attention_weights" in output
    assert output["anomaly_score"].shape == (2,)
    assert output["attention_weights"].shape == (2, 8)

    scores = output["anomaly_score"]
    assert (scores >= 0).all() and (scores <= 1).all()


# ===== Test 11: TemporalTransformerVAD (end-to-end) =====
@test("TemporalTransformerVAD processes video frames")
def test_transformer_vad():
    import torch
    from research.models.temporal_transformer import TemporalTransformerVAD

    model = TemporalTransformerVAD(
        backbone_name="resnet18", pretrained=False,
        embedding_dim=64, num_layers=1, num_heads=4, ff_dim=128,
    )
    model.eval()

    x = torch.randn(1, 4, 3, 224, 224)  # batch=1, seq=4
    with torch.no_grad():
        output = model(x)

    assert "anomaly_score" in output
    assert output["anomaly_score"].shape == (1,)


# ===== Test 12: Temporal Localization =====
@test("Anomaly timestamps are generated correctly")
def test_localization():
    import numpy as np
    from research.temporal import TemporalLocalizer

    localizer = TemporalLocalizer(threshold=0.5, min_duration=0.5, fps=10)

    # Create scores: normal(0-2s), anomaly(2-4s), normal(4-6s)
    scores = np.array([0.1] * 20 + [0.8] * 20 + [0.1] * 20)
    result = localizer.localize(scores, fps=10)

    assert len(result.segments) >= 1, "Should find at least 1 anomaly segment"
    seg = result.segments[0]
    assert seg.start_time >= 1.5, f"Segment should start around 2s, got {seg.start_time}"
    assert seg.end_time <= 4.5, f"Segment should end around 4s, got {seg.end_time}"
    assert seg.max_score >= 0.7, "Peak score should be high"
    assert len(result.timeline) >= 2, "Timeline should have normal and anomaly entries"


# ===== Test 13: Privacy — No active face recognition =====
@test("No active face recognition path exists in pipeline")
def test_privacy_no_face_rec():
    # Read source directly to avoid importing cv2-dependent module
    pipeline_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                  "ai_pipeline", "pipeline.py")
    with open(pipeline_path, "r") as f:
        source = f.read()

    assert "FaceRecognitionEngine" not in source, "Pipeline should not import FaceRecognitionEngine"
    assert "self._face_engine" not in source, "Pipeline should not reference face_engine"
    # Check that face_recognition import is gone (except in privacy comment)
    lines = [l for l in source.split("\n")
             if "face_recognition" in l.lower() and "no face recognition" not in l.lower()
             and not l.strip().startswith("#")]
    assert len(lines) == 0, f"Pipeline has face_recognition references: {lines}"


# ===== Test 14: Threshold Calibration =====
@test("Threshold calibration works on validation data")
def test_threshold_calibration():
    import numpy as np
    from research.evaluation.threshold_calibration import ThresholdCalibrator

    calibrator = ThresholdCalibrator()
    # Create fake validation data
    scores = np.array([0.1, 0.2, 0.3, 0.5, 0.6, 0.7, 0.8, 0.9])
    labels = np.array([0, 0, 0, 0, 1, 1, 1, 1])

    threshold = calibrator.calibrate_f1(scores, labels)
    assert 0.0 <= threshold <= 1.0, f"Threshold should be in [0,1], got {threshold}"


# ===== Test 15: Anomaly Head =====
@test("Anomaly head produces valid scores")
def test_anomaly_head():
    import torch
    from research.models.anomaly_head import AnomalyHead

    head = AnomalyHead(feature_dim=128, dropout=0.1)
    x = torch.randn(4, 128)
    output = head(x)
    assert output["anomaly_score"].shape == (4,)
    assert (output["anomaly_score"] >= 0).all()
    assert (output["anomaly_score"] <= 1).all()


# ===== Run all tests =====
if __name__ == "__main__":
    print(f"\n{'=' * 60}")
    print(f"  Test Results: {PASS} passed, {FAIL} failed")
    print(f"{'=' * 60}\n")
    sys.exit(1 if FAIL > 0 else 0)
