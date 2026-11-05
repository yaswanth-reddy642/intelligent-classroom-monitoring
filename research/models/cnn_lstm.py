"""CNN-LSTM baseline for Video Anomaly Detection.

Architecture:
    Video frames → CNN backbone (pretrained) → frame embeddings → LSTM → AnomalyHead → score [0,1]

The CNN backbone is configurable via timm (e.g., resnet18, efficientnet_b0).
"""

import logging
from typing import Dict, Optional

import torch
import torch.nn as nn

logger = logging.getLogger(__name__)


class CNNLSTM(nn.Module):
    """CNN-LSTM baseline for temporal anomaly detection.

    Args:
        backbone_name: timm model name for CNN feature extractor.
        pretrained: Whether to use pretrained backbone weights.
        embedding_dim: Dimension of frame embeddings after projection.
        lstm_hidden: LSTM hidden state dimension.
        lstm_layers: Number of LSTM layers.
        dropout: Dropout probability.
        num_classes: Not used directly (anomaly head outputs score).
    """

    def __init__(
        self,
        backbone_name: str = "resnet18",
        pretrained: bool = True,
        embedding_dim: int = 512,
        lstm_hidden: int = 256,
        lstm_layers: int = 2,
        dropout: float = 0.3,
    ):
        super().__init__()
        self.backbone_name = backbone_name
        self.embedding_dim = embedding_dim

        # CNN feature extractor via timm
        try:
            import timm
            self.backbone = timm.create_model(
                backbone_name, pretrained=pretrained, num_classes=0,
            )
            # Get backbone output dimension
            with torch.no_grad():
                dummy = torch.randn(1, 3, 224, 224)
                backbone_dim = self.backbone(dummy).shape[-1]
            logger.info(f"CNN backbone '{backbone_name}' loaded: output_dim={backbone_dim}")
        except ImportError:
            logger.warning("timm not installed. Using simple CNN backbone.")
            self.backbone = nn.Sequential(
                nn.Conv2d(3, 64, 7, stride=2, padding=3),
                nn.ReLU(inplace=True),
                nn.AdaptiveAvgPool2d(1),
                nn.Flatten(),
            )
            backbone_dim = 64

        # Projection to embedding_dim
        self.projection = nn.Linear(backbone_dim, embedding_dim)

        # LSTM
        self.lstm = nn.LSTM(
            input_size=embedding_dim,
            hidden_size=lstm_hidden,
            num_layers=lstm_layers,
            batch_first=True,
            dropout=dropout if lstm_layers > 1 else 0.0,
            bidirectional=False,
        )

        # Anomaly head
        from research.models.anomaly_head import AnomalyHead
        self.anomaly_head = AnomalyHead(
            feature_dim=lstm_hidden,
            dropout=dropout,
        )

        self._backbone_frozen = False

    def forward(self, x: torch.Tensor) -> Dict[str, torch.Tensor]:
        """Forward pass.

        Args:
            x: (batch, seq_len, C, H, W) video frames tensor.

        Returns:
            Dict with 'anomaly_score' (batch,) tensor in [0, 1].
        """
        batch_size, seq_len, C, H, W = x.shape

        # Extract features per frame
        x = x.view(batch_size * seq_len, C, H, W)
        features = self.backbone(x)  # (batch*seq, backbone_dim)
        features = self.projection(features)  # (batch*seq, embedding_dim)
        features = features.view(batch_size, seq_len, self.embedding_dim)

        # LSTM over sequence
        lstm_out, (h_n, _) = self.lstm(features)  # lstm_out: (batch, seq, hidden)

        # Use last hidden state
        last_hidden = h_n[-1]  # (batch, lstm_hidden)

        # Anomaly classification
        result = self.anomaly_head(last_hidden)
        return result

    def freeze_backbone(self) -> None:
        """Freeze CNN backbone parameters for transfer learning."""
        for param in self.backbone.parameters():
            param.requires_grad = False
        self._backbone_frozen = True
        logger.info("CNN backbone frozen")

    def unfreeze_backbone(self) -> None:
        """Unfreeze CNN backbone parameters."""
        for param in self.backbone.parameters():
            param.requires_grad = True
        self._backbone_frozen = False
        logger.info("CNN backbone unfrozen")

    def get_model_info(self) -> dict:
        """Return model metadata."""
        total_params = sum(p.numel() for p in self.parameters())
        trainable = sum(p.numel() for p in self.parameters() if p.requires_grad)
        return {
            "model": "CNN-LSTM",
            "backbone": self.backbone_name,
            "total_parameters": total_params,
            "trainable_parameters": trainable,
            "backbone_frozen": self._backbone_frozen,
            "embedding_dim": self.embedding_dim,
        }
