# Implementation Audit — Intelligent Classroom Monitoring

**Audit Date:** 2026-08-29
**Total Files Before Changes:** 80

## Component Status

| Component | Status | Existing File(s) | Missing | Required Action |
|-----------|--------|-------------------|---------|-----------------|
| **Video Input** | ✅ Complete | `ai_pipeline/video/video_source.py` | — | None |
| **YOLOv11 Detector** | ✅ Complete | `ai_pipeline/detection/detector.py`, `models.py` | — | None |
| **Class Mapping** | ✅ Complete | `configs/classes.yaml`, `config.py` | — | None |
| **ByteTrack Tracking** | ✅ Complete | `ai_pipeline/tracking/byte_tracker.py`, `models.py` | — | Remove face identity fields |
| **Student-Phone Association** | ✅ Complete | `ai_pipeline/association/association_engine.py`, `models.py` | Evaluation framework | Add evaluation |
| **Temporal Analyzer** | ✅ Complete | `ai_pipeline/temporal/temporal_analyzer.py`, `models.py` | — | None |
| **Context Engine** | ✅ Complete | `ai_pipeline/context/context_engine.py`, `models.py` | — | None |
| **Anomaly Scorer** | ✅ Complete | `ai_pipeline/anomaly/anomaly_scorer.py`, `models.py` | Score fusion with learned model | Add fusion module |
| **Alert Engine** | ✅ Complete | `ai_pipeline/alerts/alert_engine.py`, `evidence_capture.py` | — | None |
| **Pipeline Orchestrator** | ✅ Complete | `ai_pipeline/pipeline.py` | Learned model integration | Remove face rec, add model hook |
| **CLI Runner** | ✅ Complete | `ai_pipeline/cli.py` | — | Remove face rec flags, add privacy |
| **Configuration** | ✅ Complete | `ai_pipeline/config.py`, `configs/default_config.yaml` | Research config | Disable face rec, add research config |
| **Face Recognition** | ⚠️ MUST REMOVE | 8 files in `ai_pipeline/face_recognition/` | — | Archive and remove from pipeline |
| **FastAPI Backend** | ✅ Complete | 19 files in `backend/` | — | Remove face rec APIs |
| **React Frontend** | ✅ Complete | 19 files in `frontend/` | — | Remove enrollment, add privacy |
| **VAD Dataset** | ❌ Missing | — | Everything | Create from scratch |
| **CNN-LSTM** | ❌ Missing | — | Everything | Create from scratch |
| **Temporal Transformer** | ❌ Missing | — | Everything | Create from scratch |
| **Score Fusion** | ❌ Missing | — | Everything | Create from scratch |
| **Temporal Localization** | ❌ Missing | — | Everything | Create from scratch |
| **Threshold Calibration** | ❌ Missing | — | Everything | Create from scratch |
| **Evaluation Framework** | ❌ Missing | — | Everything | Create from scratch |
| **Experiments** | ❌ Missing | — | Everything | Create from scratch |
| **Ablation** | ❌ Missing | — | Everything | Create from scratch |
| **Robustness** | ❌ Missing | — | Everything | Create from scratch |
| **Error Analysis** | ❌ Missing | — | Everything | Create from scratch |
| **VLM Explainability** | ❌ Missing | — | Everything | Create from scratch |
| **Research Documentation** | ❌ Missing | Only README.md | Everything | Create from scratch |
| **Results Structure** | ❌ Missing | — | Everything | Create from scratch |
| **Tests** | ❌ Missing | — | Everything | Create from scratch |

## Face Recognition Touch Points

| File | Lines Affected | Type |
|------|---------------|------|
| `ai_pipeline/pipeline.py` | L20, L48, L83-109, L173, L250-252 | Import + usage |
| `ai_pipeline/config.py` | L55-64, L173, L274-286, L404-405 | Config dataclass |
| `ai_pipeline/tracking/models.py` | L32-38, L49-56, L80-84, L98-104 | Identity fields |
| `ai_pipeline/tracking/byte_tracker.py` | L208-250 | update_identity() |
| `ai_pipeline/cli.py` | face-recognition flag | CLI arg |
| `backend/app/api/students.py` | Entire file | Face enrollment API |
| `backend/app/main.py` | L55 | Description text |
| `backend/app/services/inference_service.py` | face_engine refs | Service |
| `frontend/src/pages/Enrollment.jsx` | Entire file | Face enrollment UI |
| `frontend/src/pages/Students.jsx` | Enrollment link | Link |
| `frontend/src/App.jsx` | /enrollment route | Route |
| `configs/default_config.yaml` | L38-47 | Config section |
| `requirements.txt` | L18-19 | Dependencies |
