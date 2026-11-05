# Dataset Documentation

## VAD (Video Anomaly Detection) Datasets

### Directory Structure

```
data/vad/
├── raw/              # Original videos (not committed to git)
├── processed/        # Preprocessed frames
├── train/            # Training split
├── val/              # Validation split
├── test/             # Test split
├── annotations/      # Labels (JSON/CSV)
├── sequences/        # Pre-built temporal sequences
└── split_manifest.json  # Video-level split manifest
```

### Supported Datasets

#### ShanghaiTech Campus
- **Source:** https://svip-lab.github.io/dataset/campus_dataset.html
- **Content:** 130 anomalous events across 13 scenes
- **Labels:** Frame-level anomaly annotations
- **Usage:** General video anomaly detection benchmark

#### UCSD Ped2
- **Source:** http://www.svcl.ucsd.edu/projects/anomaly/dataset.html
- **Content:** Pedestrian walkway anomalies (bikes, skaters, carts)
- **Labels:** Frame-level with pixel masks
- **Usage:** Anomaly detection benchmark

#### UCF-Crime
- **Source:** https://www.crcv.ucf.edu/projects/real-world/
- **Content:** 1900 surveillance videos with 13 anomaly types
- **Labels:** Video-level labels
- **Usage:** Large-scale weakly-supervised benchmark

### Data Preparation

1. Download dataset from official source
2. Place videos in `data/vad/raw/{dataset_name}/`
3. Run dataset validator:
   ```bash
   python -c "from research.datasets.dataset_validator import DatasetValidator; DatasetValidator().validate_structure('data/vad')"
   ```
4. Generate split manifest (video-level splits, no leakage):
   ```bash
   python -c "
   from research.datasets.split_validator import SplitValidator
   sv = SplitValidator()
   manifest = sv.create_split_manifest(videos, ratios=[0.7, 0.15, 0.15], seed=42)
   sv.save_manifest(manifest, 'data/vad/split_manifest.json')
   "
   ```

### Anomaly Label Schema

| Label | Code | Description |
|-------|------|-------------|
| NORMAL | 0 | Normal classroom activity |
| POTENTIAL_PHONE_USAGE | 1 | Potential unauthorized phone use |
| AUTHORIZED_PHONE_ACTIVITY | 2 | Approved phone use (e.g., educational app) |
| AMBIGUOUS | 3 | Unclear activity |
| OTHER_ANOMALY | 4 | Non-phone anomaly |

See `research/datasets/anomaly_schema.md` for full schema documentation.

### Data Leakage Prevention

**CRITICAL:** Video-level splits are enforced. Frames from the same video NEVER appear in different splits.

```
✅ Correct: Video A → train, Video B → val, Video C → test
❌ Wrong:   Video A frame1 → train, Video A frame2 → test
```

Use `research/datasets/split_validator.py` to validate splits.
