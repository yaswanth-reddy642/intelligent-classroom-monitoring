"""Integration adapter — connects learned temporal models to the classroom pipeline.

Provides a clean interface between the research models (CNN-LSTM or Temporal Transformer)
and the existing application pipeline.
"""

import logging
import time
from typing import Optional, Dict, Any, List
from collections import deque

import numpy as np

logger = logging.getLogger(__name__)


class TemporalAnomalyAdapter:
    """Adapter connecting a learned temporal anomaly model to the pipeline.

    Collects frame-level features over time, builds temporal sequences,
    and feeds them to the learned model for anomaly scoring.

    Usage:
        adapter = TemporalAnomalyAdapter(model, config)
        pipeline.set_temporal_model(adapter)

    The pipeline calls adapter.predict(features) per frame, and the adapter
    accumulates features into sequences, running inference when a full
    sequence is available.
    """

    def __init__(
        self,
        model,
        sequence_length: int = 16,
        model_name: str = "unknown",
        model_version: str = "1.0",
        device: str = "cpu",
    ):
        """Initialize the adapter.

        Args:
            model: PyTorch model with forward() method. Expected to accept
                   tensor of shape (1, seq_len, embedding_dim) and return
                   dict with 'anomaly_score'.
            sequence_length: Number of frames per sequence.
            model_name: Name for metadata.
            model_version: Version for metadata.
            device: torch device string.
        """
        self._model = model
        self._seq_len = sequence_length
        self._model_name = model_name
        self._model_version = model_version
        self._device = device

        # Feature buffer (sliding window)
        self._buffer: deque = deque(maxlen=sequence_length)
        self._last_score: Optional[float] = None
        self._inference_count = 0

        # Put model in eval mode
        self._model.eval()
        logger.info(
            f"TemporalAnomalyAdapter initialized: model={model_name}, "
            f"seq_len={sequence_length}, device={device}"
        )

    def predict(self, features: Optional[np.ndarray] = None) -> Dict[str, Any]:
        """Run prediction with accumulated features.

        Args:
            features: Frame-level feature vector (1D numpy array).
                     If None, uses the last available score.

        Returns:
            Dict with anomaly_score, model_name, model_version, timestamp.
        """
        result = {
            "anomaly_score": None,
            "model_name": self._model_name,
            "model_version": self._model_version,
            "timestamp": time.time(),
            "sequence_ready": False,
        }

        if features is not None:
            self._buffer.append(features)

        # Only predict when we have a full sequence
        if len(self._buffer) < self._seq_len:
            result["anomaly_score"] = self._last_score
            return result

        try:
            import torch

            # Build sequence tensor
            seq = np.stack(list(self._buffer), axis=0)  # (seq_len, feat_dim)
            seq_tensor = torch.FloatTensor(seq).unsqueeze(0).to(self._device)

            with torch.no_grad():
                output = self._model(seq_tensor)

            score = output["anomaly_score"]
            if isinstance(score, torch.Tensor):
                score = score.item()

            self._last_score = float(score)
            self._inference_count += 1
            result["anomaly_score"] = self._last_score
            result["sequence_ready"] = True

        except Exception as e:
            logger.error(f"Temporal model inference error: {e}")
            result["anomaly_score"] = self._last_score

        return result

    def reset(self) -> None:
        """Clear the feature buffer."""
        self._buffer.clear()
        self._last_score = None

    @property
    def is_ready(self) -> bool:
        """Whether enough features have been collected for inference."""
        return len(self._buffer) >= self._seq_len

    @property
    def inference_count(self) -> int:
        return self._inference_count


def load_temporal_model(
    model_type: str,
    checkpoint_path: str,
    config: dict,
    device: str = "cpu",
) -> Optional[TemporalAnomalyAdapter]:
    """Load a learned temporal model and wrap it in an adapter.

    Args:
        model_type: 'cnn_lstm' or 'temporal_transformer'.
        checkpoint_path: Path to model checkpoint.
        config: Model configuration dict.
        device: Torch device.

    Returns:
        TemporalAnomalyAdapter or None if loading fails.
    """
    try:
        import torch

        if model_type == "cnn_lstm":
            from research.models.cnn_lstm import CNNLSTM
            model = CNNLSTM(
                backbone_name=config.get("backbone", "resnet18"),
                embedding_dim=config.get("embedding_dim", 512),
                lstm_hidden=config.get("lstm_hidden", 256),
                lstm_layers=config.get("lstm_layers", 2),
                dropout=config.get("dropout", 0.3),
            )
        elif model_type == "temporal_transformer":
            from research.models.temporal_transformer import TemporalTransformer
            model = TemporalTransformer(
                embedding_dim=config.get("embedding_dim", 512),
                num_layers=config.get("num_layers", 4),
                num_heads=config.get("num_heads", 8),
                ff_dim=config.get("ff_dim", 2048),
                dropout=config.get("dropout", 0.1),
            )
        else:
            logger.error(f"Unknown model type: {model_type}")
            return None

        # Load checkpoint
        checkpoint = torch.load(checkpoint_path, map_location=device)
        if "model_state_dict" in checkpoint:
            model.load_state_dict(checkpoint["model_state_dict"])
        else:
            model.load_state_dict(checkpoint)

        model.to(device)
        model.eval()

        adapter = TemporalAnomalyAdapter(
            model=model,
            sequence_length=config.get("sequence_length", 16),
            model_name=model_type,
            model_version=config.get("version", "1.0"),
            device=device,
        )

        logger.info(f"Loaded temporal model: {model_type} from {checkpoint_path}")
        return adapter

    except Exception as e:
        logger.error(f"Failed to load temporal model {model_type}: {e}")
        return None
