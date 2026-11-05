# Base Paper Documentation

## Detection Foundation

### YOLOv11 (Ultralytics, 2024)
- **Framework:** Ultralytics YOLO v11
- **Architecture:** CSPDarknet backbone + PAN-FPN neck + decoupled detection head
- **Training:** Pre-trained on COCO (80 classes)
- **Classes used:** person (class 0), cell phone (class 67)
- **Implementation:** `ai_pipeline/detection/detector.py`

## Video Anomaly Detection Literature

### Foundational Works

1. **Sultani et al. (2018)** — "Real-World Anomaly Detection in Surveillance Videos"
   - UCF-Crime dataset, MIL-based ranking loss
   - Established weakly-supervised VAD paradigm

2. **Liu et al. (2018)** — "Future Frame Prediction for Anomaly Detection"
   - ShanghaiTech dataset, prediction-based anomaly scoring
   - Frame-level AUC benchmark

3. **Tian et al. (2021)** — "Weakly-supervised Video Anomaly Detection with Robust Temporal Feature Magnitude Learning"
   - RTFM: top-k feature magnitude selection
   - Strong baseline for MIL-based VAD

### Temporal Transformer for VAD

4. **Feng et al. (2021)** — "MIST: Multiple Instance Self-Training for VAD"
   - Self-training with pseudo labels

5. **Zhang et al. (2023)** — Various Transformer-based VAD approaches
   - Temporal attention for anomaly detection
   - Our work extends this direction with classroom-specific context

## Reproduction Approach

### What Can Be Reproduced
- Standard YOLOv11 detection with COCO weights (exact reproduction)
- CNN-LSTM architecture following established VAD baselines
- Temporal Transformer following standard encoder architecture

### What Is Adapted
- Classroom-specific phone detection pipeline
- Context-aware scoring (LECTURE/EXAM/BREAK)
- Student-phone spatial association
- Score fusion between learned and rule-based systems

### Why Adaptation Is Necessary
- No existing paper directly addresses temporal phone-use anomaly detection
- Classroom monitoring requires domain-specific context modeling
- Standard VAD datasets lack phone-use annotations
- The contribution is the integration of temporal deep learning with classroom-specific pipelines

## YOLO-CBR Enhanced Detector

**Status:** Base paper selection pending.

For the enhanced detector experiment (Level 2), the selected paper should document:
- Original paper: [Title, authors, year, DOI]
- Architecture modifications applied
- What was reproduced vs adapted
- Any deviations and justification

This section will be updated when a specific base paper is selected.
