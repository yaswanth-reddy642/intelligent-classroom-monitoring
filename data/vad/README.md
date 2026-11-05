# VAD Dataset Directory

This directory stores Video Anomaly Detection (VAD) datasets.

## Structure

```
data/vad/
├── raw/              # Original video files
├── processed/        # Extracted/preprocessed frames
├── train/            # Training split
├── val/              # Validation split
├── test/             # Test split
├── annotations/      # Anomaly labels (JSON/CSV)
├── sequences/        # Pre-built temporal sequences
└── split_manifest.json
```

## Obtaining Datasets

### ShanghaiTech Campus
1. Visit: https://svip-lab.github.io/dataset/campus_dataset.html
2. Download the dataset
3. Place videos in `raw/shanghaitech/`

### UCSD Ped2
1. Visit: http://www.svcl.ucsd.edu/projects/anomaly/dataset.html
2. Download UCSD Anomaly Detection Dataset
3. Place in `raw/ucsd_ped2/`

### UCF-Crime
1. Visit: https://www.crcv.ucf.edu/projects/real-world/
2. Download UCF-Crime dataset
3. Place in `raw/ucf_crime/`

**Note:** Do NOT commit large video files to git. Use `.gitignore` to exclude `raw/` and `processed/`.

## Data Preparation

See `docs/DATASET.md` for full preparation instructions.
