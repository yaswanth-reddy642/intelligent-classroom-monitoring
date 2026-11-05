# Intelligent Classroom Monitoring and Anomaly Detection Using YOLOv11

B.Tech Major Project — Research-Oriented Computer Vision Application

> **Privacy Notice:** This system uses anonymous tracking identifiers (ST-001, ST-002, etc.). No facial identity recognition is performed.

## Overview

A complete, modular, production-style intelligent classroom monitoring system that:
- Detects students and mobile phones using **YOLOv11**
- Tracks objects with persistent anonymous IDs using **ByteTrack**
- Associates students with nearby phones via **spatial proximity**
- Performs **temporal behavior analysis** (phone usage duration)
- Applies **context-aware anomaly scoring** (LECTURE/EXAM/BREAK)
- Generates **real-time alerts** with evidence capture
- Provides a **FastAPI REST API** with **WebSocket** streaming
- Features a **React dashboard** for monitoring
- Includes **CNN-LSTM** and **Temporal Transformer** research models
- Supports **optional VLM explainability** for detected anomalies

## Architecture

```
Video → YOLOv11 → ByteTrack → Association → Temporal → Context → Anomaly → Alert
                                                          ↑
                                               CNN-LSTM / Transformer
                                                  (learned model)
```

## Quick Start

```bash
# Install
pip install -r requirements.txt

# Run AI Pipeline (standalone)
python -m ai_pipeline.cli --source video.mp4

# Run Backend
cd backend && uvicorn app.main:app --reload

# Run Frontend
cd frontend && npm install && npm run dev
```

## Project Structure

```
ai_pipeline/          # Core AI pipeline (detection, tracking, association, anomaly)
research/             # Research models, evaluation, experiments
├── models/           # CNN-LSTM, Temporal Transformer
├── datasets/         # VAD dataset pipeline
├── training/         # Training scripts
├── evaluation/       # Metrics and benchmarking
├── experiments/      # Experiment runners (ablation, robustness)
├── analysis/         # Error analysis (FP/FN)
├── explainability/   # VLM explanation
└── integration/      # Pipeline adapter
backend/              # FastAPI REST API + MongoDB
frontend/             # React + Vite + Tailwind dashboard
configs/              # Configuration YAML files
docs/                 # Documentation
results/              # Experiment results (CSV)
tests/                # Test suite
```

## Research Components

| Component | File | Status |
|-----------|------|--------|
| CNN-LSTM Baseline | `research/models/cnn_lstm.py` | Implemented |
| Temporal Transformer | `research/models/temporal_transformer.py` | Implemented |
| VAD Dataset | `research/datasets/vad_dataset.py` | Implemented |
| Score Fusion | `ai_pipeline/anomaly/fusion.py` | Implemented |
| Temporal Localization | `research/temporal/localizer.py` | Implemented |
| Threshold Calibration | `research/evaluation/threshold_calibration.py` | Implemented |
| Ablation Study | `research/experiments/run_ablation.py` | Implemented |
| Robustness Tests | `research/experiments/run_robustness.py` | Implemented |
| Error Analysis | `research/analysis/` | Implemented |
| VLM Explanation | `research/explainability/` | Implemented (optional) |

## Documentation

- [Setup Guide](docs/SETUP.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Research](docs/RESEARCH.md)
- [Dataset](docs/DATASET.md)
- [Experiments](docs/EXPERIMENTS.md)
- [Privacy](docs/PRIVACY.md)

## Key Commands

```bash
# Train CNN-LSTM
python -m research.training.train_vad --config configs/research_config.yaml

# Train Transformer
python -m research.training.train_transformer --config configs/research_config.yaml

# Run ablation
python -m research.experiments.run_ablation --output-dir results/ablation

# Run tests
python tests/test_system.py
```

## License

For academic/research use only.
"# intelligent-classroom-monitoring" 
