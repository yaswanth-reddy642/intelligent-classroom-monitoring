"""Anomaly classification head — shared by CNN-LSTM and Temporal Transformer.

Takes a feature vector and outputs an anomaly score in [0, 1].
"""

import torch
import torch.nn as nn
from typing import Dict


class AnomalyHead(nn.Module):
    """MLP anomaly classification head.

    Architecture:
        feature_dim → hidden → dropout → hidden/2 → dropout → 1 → sigmoid

    Args:
        feature_dim: Input feature dimension.
        hidden_dim: Hidden layer dimension (default: feature_dim // 2).
        dropout: Dropout probability.
    """

    def __init__(
        self,
        feature_dim: int,
        hidden_dim: int = 0,
        dropout: float = 0.3,
    ):
        super().__init__()
        hidden_dim = hidden_dim or feature_dim // 2

        self.head = nn.Sequential(
            nn.Linear(feature_dim, hidden_dim),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim // 2, 1),
            nn.Sigmoid(),
        )

    def forward(self, features: torch.Tensor) -> Dict[str, torch.Tensor]:
        """Forward pass.

        Args:
            features: (batch, feature_dim) tensor.

        Returns:
            Dict with 'anomaly_score' (batch,) and 'features' (batch, feature_dim).
        """
        score = self.head(features).squeeze(-1)
        return {"anomaly_score": score, "features": features}
