# Literature Comparison

## Comparison with Existing Work

| Aspect | Standard VAD | Phone Detection | Our System |
|--------|-------------|-----------------|------------|
| Detection | Generic (person, car) | Phone detection only | YOLOv11 (person + phone) |
| Tracking | Optional | None | ByteTrack (persistent IDs) |
| Association | N/A | N/A | Student-phone spatial association |
| Temporal | LSTM/Transformer | Frame-level | Application + Learned temporal |
| Context | None | None | LECTURE/EXAM/BREAK scoring |
| Privacy | Varies | Varies | Anonymous tracking only |
| Explainability | None | None | Optional VLM explanation |
| Evaluation | AUC/F1 | P/R/F1 | Full ablation + robustness |

## Research Gap

1. **No temporal modeling in phone detection** — Existing classroom phone detection uses frame-level alerting, causing excessive false positives from momentary phone appearances.

2. **No context-aware scoring** — Existing systems treat all phone detections equally regardless of classroom activity mode.

3. **No learned temporal model for classroom anomaly** — VAD models exist for surveillance but not specifically for classroom phone-use temporal patterns.

4. **No score fusion framework** — No existing work combines learned temporal anomaly scores with rule-based context-aware scores in a configurable way.
