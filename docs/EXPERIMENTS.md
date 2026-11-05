# Experiments Guide

## Experiment Matrix

See `research/experiments/experiment_matrix.yaml` for all E1-E12 experiments.

## Quick Start

### 1. Train CNN-LSTM Baseline
```bash
python -m research.training.train_vad \
    --config configs/research_config.yaml \
    --epochs 50 --seed 42 \
    --output-dir results/vad/cnn_lstm
```

### 2. Train Temporal Transformer
```bash
python -m research.training.train_transformer \
    --config configs/research_config.yaml \
    --epochs 50 --seed 42 \
    --output-dir results/vad/transformer
```

### 3. Multiple Seeds (for mean ± std)
```bash
for seed in 42 123 456; do
    python -m research.training.train_vad --seed $seed --output-dir results/vad/cnn_lstm/seed_$seed
    python -m research.training.train_transformer --seed $seed --output-dir results/vad/transformer/seed_$seed
done
```

### 4. Run Ablation Study
```bash
python -m research.experiments.run_ablation \
    --config configs/research_config.yaml \
    --output-dir results/ablation
```

### 5. Run Robustness Tests
```bash
python -m research.experiments.run_robustness \
    --config configs/research_config.yaml \
    --output-dir results/robustness
```

### 6. Frame-Level vs Temporal Comparison
```bash
python -m research.experiments.run_frame_vs_temporal \
    --source test_video.mp4 \
    --output-dir results/anomaly
```

### 7. Context vs No-Context Comparison
```bash
python -m research.experiments.run_context_experiment \
    --source test_video.mp4 \
    --output-dir results/anomaly
```

### 8. Detector Comparison
```bash
python -m research.experiments.run_detector_comparison \
    --source test_video.mp4 \
    --output-dir results/detection
```

### 9. End-to-End Performance Benchmark
```bash
python -m research.evaluation.evaluate_performance \
    --source test_video.mp4 \
    --output results/performance/performance_results.csv
```

## Result Files

All results are saved as CSV files in `results/`:

| File | Location |
|------|----------|
| Training curves | `results/vad/{model}/training_metrics.csv` |
| VAD metrics | `results/vad/vad_metrics.csv` |
| Ablation | `results/ablation/ablation_results.csv` |
| Robustness | `results/robustness/robustness_results.csv` |
| Performance | `results/performance/performance_results.csv` |
| Association | `results/association/association_metrics.csv` |
| Detection | `results/detection/detection_metrics.csv` |

## Important Notes

- **No fabricated results.** All CSV files contain "N/A" for unrun experiments.
- **No test-set threshold selection.** Use `threshold_calibration.py` on validation data only.
- **Video-level splits.** Data leakage is prevented by `split_validator.py`.
- **Seed reproducibility.** Always specify `--seed` for reproducible results.
