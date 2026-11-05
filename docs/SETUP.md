# Setup Guide

## Prerequisites

- Python 3.10 or 3.11
- pip or conda
- MongoDB (for backend)
- Node.js 18+ (for frontend)
- CUDA-compatible GPU (recommended, not required)

## 1. Python Environment

```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

## 2. YOLOv11 Model

The model is downloaded automatically on first run. To pre-download:

```bash
python -c "from ultralytics import YOLO; YOLO('yolo11n.pt')"
```

Model will be saved to `models/yolo11n.pt`.

## 3. MongoDB

Install MongoDB Community Server and start the service:

```bash
# Default connection: mongodb://localhost:27017
# Database: classroom_monitoring
```

## 4. Configuration

Copy and edit the config file:

```bash
cp configs/default_config.yaml configs/local_config.yaml
# Edit local_config.yaml with your settings
```

Key settings:
- `video.source_type`: webcam, file, rtsp
- `detection.device`: auto, cpu, cuda
- `context.default_mode`: LECTURE, EXAM, BREAK

## 5. Run AI Pipeline (Standalone)

```bash
# With webcam
python -m ai_pipeline.cli --source webcam

# With video file
python -m ai_pipeline.cli --source path/to/video.mp4

# Without display (headless)
python -m ai_pipeline.cli --source video.mp4 --no-display
```

## 6. Run Backend

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 7. Run Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend at http://localhost:5173, API at http://localhost:8000.

## 8. Research Training

```bash
# Train CNN-LSTM baseline
python -m research.training.train_vad --config configs/research_config.yaml --epochs 50

# Train Temporal Transformer
python -m research.training.train_transformer --config configs/research_config.yaml --epochs 50
```

See [EXPERIMENTS.md](EXPERIMENTS.md) for full experiment instructions.

## 9. Research Data

See [DATASET.md](DATASET.md) for dataset preparation.
