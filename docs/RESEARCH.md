# Research Documentation

## 1. Base Paper

### Selected Foundation

The system builds upon the YOLOv11 object detection framework as the primary detection backbone. The research extends standard YOLO-based detection with temporal deep learning for video anomaly detection in classroom environments.

**Base detection framework:**
- **Model:** YOLOv11 (Ultralytics, 2024)
- **Architecture:** CSPDarknet backbone + PAN-FPN neck + detection head
- **Training:** COCO pretrained weights (person=class 0, cell phone=class 67)

### YOLO-CBR Enhanced Detector Notes

For the enhanced detector comparison (Level 2), the system documents adaptations inspired by attention-enhanced YOLO variants from recent literature. Specific modifications should reference the selected base paper. If exact reproduction is not possible, document:

- Original paper title, authors, year, DOI
- What was reproducible vs what was adapted
- Why adaptation was necessary

**Status:** Base paper selection pending. The experiment framework is ready in `research/experiments/run_detector_comparison.py`.

## 2. Research Gap

Current YOLO-based classroom monitoring systems:
- Rely on frame-level detection without temporal modeling
- Do not distinguish between authorized and unauthorized phone activity
- Generate excessive false positives from momentary detections
- Lack explainability for detected anomalies

## 3. Problem Statement

Design and evaluate a temporal deep-learning extension to YOLOv11-based classroom monitoring that:
1. Reduces false-positive alerts through temporal verification
2. Improves anomaly detection through learned temporal patterns
3. Supports context-aware scoring (lecture vs exam vs break)
4. Provides optional VLM-based explanation for detected events

## 4. Baseline — CNN-LSTM

Architecture: CNN (ResNet-18) → frame embeddings → LSTM → anomaly score

Implementation: `research/models/cnn_lstm.py`

## 5. Proposed Method — Temporal Transformer

Architecture: CNN → frame embeddings → positional encoding → Transformer encoder → temporal attention pooling → anomaly score

Implementation: `research/models/temporal_transformer.py`

## 6. Dataset

Supports: ShanghaiTech, UCSD Ped2, UCF-Crime, custom classroom data

Pipeline: `research/datasets/vad_dataset.py`

Video-level splits enforced (no data leakage): `research/datasets/split_validator.py`

## 7. Metrics

- Precision, Recall, F1-score
- ROC-AUC, PR-AUC
- FPR, FNR
- End-to-end FPS and latency

## 8. Experimental Protocol

1. Train CNN-LSTM baseline (3 seeds)
2. Train Temporal Transformer (3 seeds)
3. Compare on same test set
4. Run ablation study (9 configurations)
5. Run robustness evaluation (8 conditions)
6. Run error analysis (FP/FN categorization)
7. Measure computational cost

See: `research/experiments/experiment_matrix.yaml`

## 9. Ablation

| Config | Components |
|--------|-----------|
| A1 | YOLOv11 only |
| A2 | + ByteTrack |
| A3 | + Association |
| A4 | + Temporal verification |
| A5 | + Context scoring |
| A6 | CNN-LSTM |
| A7 | Temporal Transformer |
| A8 | Transformer + context |
| A9 | Full proposed system |

## 10. Robustness Conditions

1. Normal classroom
2. Occlusion
3. Small mobile phones
4. Crowded classroom
5. Low-light video
6. Motion blur
7. Camera angle variation
8. Temporary missed detections

## 11. Computational Cost

For each model report: parameter count, model size, GPU memory, inference latency, FPS, training time

## 12. Limitations

- Dependent on COCO-pretrained detection quality for phone class
- Temporal models require training data which may be limited
- VLM explanation requires external API and adds latency
- System cannot determine actual exam misconduct — it detects potential anomalous activity only

## 13. Future Work

- Fine-tune YOLOv11 on classroom-specific dataset
- Multi-camera tracking
- Online learning for temporal models
- Lightweight model distillation for edge deployment
