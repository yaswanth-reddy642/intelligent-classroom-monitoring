"""Training utilities — reproducibility, early stopping, experiment tracking."""

import logging
import os
import random
import time
import json
import platform
import csv
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


def set_seed(seed: int) -> None:
    """Set random seed for reproducibility across random, numpy, torch."""
    random.seed(seed)
    np.random.seed(seed)
    try:
        import torch
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
            torch.backends.cudnn.deterministic = True
            torch.backends.cudnn.benchmark = False
    except ImportError:
        pass
    logger.info(f"Random seed set to {seed}")


class EarlyStopping:
    """Early stopping to halt training when validation metric stops improving.

    Args:
        patience: Number of epochs to wait before stopping.
        min_delta: Minimum change to qualify as improvement.
        mode: 'min' for loss (lower is better), 'max' for metrics (higher is better).
    """

    def __init__(self, patience: int = 10, min_delta: float = 0.0, mode: str = "min"):
        self.patience = patience
        self.min_delta = min_delta
        self.mode = mode
        self.counter = 0
        self.best_value = float("inf") if mode == "min" else float("-inf")
        self.should_stop = False

    def __call__(self, value: float) -> bool:
        """Check if training should stop.

        Returns True if training should stop.
        """
        if self.mode == "min":
            improved = value < self.best_value - self.min_delta
        else:
            improved = value > self.best_value + self.min_delta

        if improved:
            self.best_value = value
            self.counter = 0
        else:
            self.counter += 1
            if self.counter >= self.patience:
                self.should_stop = True
                logger.info(f"Early stopping triggered after {self.counter} epochs without improvement")

        return self.should_stop


def get_hardware_info() -> dict:
    """Collect hardware and software information for experiment metadata."""
    info = {
        "platform": platform.platform(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
    }
    try:
        import torch
        info["torch_version"] = torch.__version__
        info["cuda_available"] = torch.cuda.is_available()
        if torch.cuda.is_available():
            info["gpu_name"] = torch.cuda.get_device_name(0)
            info["gpu_memory_mb"] = round(torch.cuda.get_device_properties(0).total_mem / 1e6, 0)
            info["cuda_version"] = torch.version.cuda
    except ImportError:
        info["torch_version"] = "not installed"
        info["cuda_available"] = False
    return info


@dataclass
class ExperimentMetadata:
    """Metadata for a single experiment run."""
    experiment_id: str
    timestamp: str = ""
    model: str = ""
    dataset: str = ""
    device: str = ""
    seed: int = 42
    config_snapshot: dict = field(default_factory=dict)
    hardware_info: dict = field(default_factory=dict)
    notes: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
        if not self.hardware_info:
            self.hardware_info = get_hardware_info()


def save_experiment_metadata(metadata: ExperimentMetadata, path: str) -> None:
    """Save experiment metadata to JSON."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(asdict(metadata), f, indent=2, default=str)
    logger.info(f"Experiment metadata saved: {path}")


class MetricTracker:
    """Tracks training/validation metrics per epoch."""

    def __init__(self):
        self.history: Dict[str, List[float]] = {}

    def update(self, metrics: dict) -> None:
        """Record metrics for the current epoch."""
        for key, value in metrics.items():
            if key not in self.history:
                self.history[key] = []
            self.history[key].append(value)

    def get_best(self, metric: str, mode: str = "min") -> tuple:
        """Get best value and epoch for a metric."""
        if metric not in self.history:
            return None, -1
        values = self.history[metric]
        if mode == "min":
            best_idx = int(np.argmin(values))
        else:
            best_idx = int(np.argmax(values))
        return values[best_idx], best_idx

    def save_to_csv(self, path: str) -> None:
        """Save metric history to CSV."""
        if not self.history:
            return
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
        epochs = max(len(v) for v in self.history.values())
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            keys = sorted(self.history.keys())
            writer.writerow(["epoch"] + keys)
            for i in range(epochs):
                row = [i + 1]
                for key in keys:
                    vals = self.history[key]
                    row.append(round(vals[i], 6) if i < len(vals) else "N/A")
                writer.writerow(row)
        logger.info(f"Metrics saved to {path}")
