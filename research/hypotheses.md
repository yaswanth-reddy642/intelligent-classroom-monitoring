# Research Hypotheses

## H1 — Temporal Transformer vs CNN-LSTM

**Hypothesis:** Temporal Transformer-based modeling improves anomaly-detection performance compared with the CNN-LSTM baseline.

**Evaluation:**
- Compare precision, recall, F1, ROC-AUC on the same VAD test set
- Use multiple random seeds (42, 123, 456) and report mean ± std
- Statistical significance via paired comparison

**Status:** Not yet evaluated

---

## H2 — Temporal Verification Reduces False Positives

**Hypothesis:** Temporal verification reduces false-positive alerts compared with frame-level phone detection.

**Evaluation:**
- Experiment A: Phone detection → immediate alert
- Experiment B: Phone detection → tracking → association → temporal verification → alert
- Compare precision, recall, F1, FPR, alert count, detection latency

**Status:** Not yet evaluated

---

## H3 — Association Improves Precision

**Hypothesis:** Student-phone association improves precision compared with phone detection alone.

**Evaluation:**
- With association vs without association
- Measure precision, recall, F1 specifically for phone-related anomalies
- Test across scenarios: near/far phone, multiple students, occlusion

**Status:** Not yet evaluated

---

## H4 — Context-Aware Scoring Reduces False Alerts

**Hypothesis:** Context-aware scoring reduces false alerts during authorized phone activity.

**Evaluation:**
- Compare scoring with/without classroom context across modes (LECTURE, EXAM, AUTHORIZED_PHONE_ACTIVITY, BREAK)
- Measure reduction in false positives during AUTHORIZED_PHONE_ACTIVITY and BREAK
- Measure overall precision and false alert count

**Status:** Not yet evaluated

---

## H5 — Real-Time Performance

**Hypothesis:** The proposed system maintains acceptable real-time performance under practical classroom video conditions.

**Evaluation:**
- End-to-end FPS measurement (not just YOLO FPS)
- Per-stage latency breakdown
- Compare with/without learned temporal model
- Test at different resolutions and with different numbers of tracked objects

**Acceptance criteria:** ≥15 FPS at 640×640 on GPU, ≥5 FPS on CPU

**Status:** Not yet evaluated
