# System Architecture

## Pipeline Flow

```
Video / CCTV
      ↓
Frame Sampling (configurable skip)
      ↓
YOLOv11 Object Detection
      ↓
Student + Mobile Phone Detection
      ↓
ByteTrack Multi-Object Tracking
      ↓
Anonymous Tracking IDs (ST-001, P-001)
      ↓
Student-Phone Association (spatial + temporal)
      ↓
Application Temporal Verification (sliding window)
      ↓
[Optional] CNN-LSTM / Temporal Transformer → Learned Anomaly Score
      ↓
Context-Aware Scoring (LECTURE/EXAM/BREAK)
      ↓
Score Fusion (learned + context)
      ↓
[Optional] Temporal Anomaly Localization
      ↓
Alert Generation (with cooldown)
      ↓
Evidence Capture
      ↓
MongoDB / WebSocket / Dashboard
      ↓
[Optional] VLM Explanation
```

## Module Structure

```
ai_pipeline/
├── config.py                  # Master configuration (dataclasses + YAML)
├── pipeline.py                # Pipeline orchestrator
├── cli.py                     # CLI runner
├── detection/
│   ├── detector.py            # YOLOv11 wrapper
│   └── models.py              # Detection data models
├── tracking/
│   ├── byte_tracker.py        # ByteTrack wrapper
│   └── models.py              # TrackedObject (anonymous IDs)
├── association/
│   ├── association_engine.py   # Student-phone spatial association
│   └── models.py              # Association data models
├── temporal/
│   ├── temporal_analyzer.py   # Sliding-window phone duration analysis
│   └── models.py              # Temporal data models
├── context/
│   ├── context_engine.py      # Classroom context mode management
│   └── models.py              # Context data models
├── anomaly/
│   ├── anomaly_scorer.py      # Rule-based anomaly scoring (A=w1D+w2S+w3T+w4C)
│   ├── fusion.py              # Learned + context score fusion
│   └── models.py              # Anomaly data models
├── alerts/
│   ├── alert_engine.py        # Alert generation with cooldown
│   └── evidence_capture.py    # Evidence frame saving
└── video/
    └── video_source.py        # Video input (webcam/file/RTSP)

research/
├── models/
│   ├── anomaly_head.py        # Shared anomaly classification head
│   ├── cnn_lstm.py            # CNN-LSTM baseline
│   └── temporal_transformer.py # Temporal Transformer (proposed)
├── datasets/
│   ├── vad_dataset.py         # VAD PyTorch Dataset
│   ├── sequence_builder.py    # Temporal sequence generation
│   ├── split_validator.py     # Data leakage prevention
│   └── dataset_validator.py   # Dataset structure validation
├── training/
│   ├── train_vad.py           # CNN-LSTM training
│   ├── train_transformer.py   # Transformer training
│   └── trainer_utils.py       # Seeds, early stopping, metrics
├── evaluation/
│   ├── evaluate_vad.py        # VAD metrics (P/R/F1/AUC)
│   ├── evaluate_association.py # Association evaluation
│   ├── evaluate_context.py    # Context comparison
│   ├── evaluate_performance.py # Latency benchmarking
│   └── threshold_calibration.py # Threshold selection
├── experiments/
│   ├── run_ablation.py        # 9-config ablation study
│   ├── run_robustness.py      # 8-condition robustness test
│   └── experiment_matrix.yaml # E1-E12 experiment definitions
├── temporal/
│   └── localizer.py           # Temporal anomaly localization
├── analysis/
│   ├── false_positive_analyzer.py
│   └── false_negative_analyzer.py
├── explainability/
│   ├── evidence_selector.py   # Evidence frame selection
│   ├── vlm_explainer.py       # VLM API integration
│   └── explanation_service.py # Orchestration
├── integration/
│   └── temporal_anomaly_adapter.py # Pipeline integration
└── visualization/
    └── chart_generator.py     # Publication-quality charts

backend/                        # FastAPI + MongoDB
frontend/                       # React + Vite + Tailwind
```

## Anomaly Scoring

### Rule-Based (Application)
```
A = w1·D + w2·S + w3·T + w4·C
```
- D = phone detection confidence (w1=0.25)
- S = student-phone association score (w2=0.25)
- T = temporal persistence ratio (w3=0.30)
- C = context multiplier (w4=0.20)

### Score Fusion (with Learned Model)
```
A_final = f(A_learned, A_context)
```
- Modes: weighted_average, max, learned_only, context_only
- Configurable weights in `configs/research_config.yaml`
