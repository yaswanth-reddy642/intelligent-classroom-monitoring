"""Temporal Transformer for Video Anomaly Detection.

Primary research extension. Architecture:
    Frame embeddings → Positional Encoding → Transformer Encoder
    → Temporal Attention Pooling → AnomalyHead → anomaly score [0,1]

Also provides TemporalTransformerVAD which wraps a CNN backbone
+ TemporalTransformer for end-to-end video input.
"""

import logging
import math
from typing import Dict, Optional

import torch
import torch.nn as nn

logger = logging.getLogger(__name__)


class PositionalEncoding(nn.Module):
    """Learnable positional encoding for temporal sequences."""

    def __init__(self, d_model: int, max_len: int = 512, dropout: float = 0.1):
        super().__init__()
        self.dropout = nn.Dropout(p=dropout)
        self.pos_embedding = nn.Parameter(torch.randn(1, max_len, d_model) * 0.02)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Add positional encoding. x: (batch, seq_len, d_model)."""
        seq_len = x.size(1)
        x = x + self.pos_embedding[:, :seq_len, :]
        return self.dropout(x)


class TemporalAttentionPooling(nn.Module):
    """Attention-based pooling over temporal dimension.

    Instead of mean pooling, learns attention weights over sequence
    positions to produce a single summary vector.
    """

    def __init__(self, d_model: int):
        super().__init__()
        self.attention = nn.Sequential(
            nn.Linear(d_model, d_model // 2),
            nn.Tanh(),
            nn.Linear(d_model // 2, 1),
        )

    def forward(self, x: torch.Tensor) -> tuple:
        """Pool over temporal dimension.

        Args:
            x: (batch, seq_len, d_model)

        Returns:
            pooled: (batch, d_model)
            weights: (batch, seq_len) attention weights
        """
        attn_logits = self.attention(x).squeeze(-1)  # (batch, seq_len)
        attn_weights = torch.softmax(attn_logits, dim=-1)  # (batch, seq_len)
        pooled = torch.bmm(attn_weights.unsqueeze(1), x).squeeze(1)  # (batch, d_model)
        return pooled, attn_weights


class TemporalTransformer(nn.Module):
    """Temporal Transformer encoder for sequence-level anomaly detection.

    Args:
        embedding_dim: Input/output feature dimension.
        num_layers: Number of Transformer encoder layers.
        num_heads: Number of attention heads.
        ff_dim: Feed-forward hidden dimension.
        dropout: Dropout probability.
        max_seq_len: Maximum supported sequence length.
    """

    def __init__(
        self,
        embedding_dim: int = 512,
        num_layers: int = 4,
        num_heads: int = 8,
        ff_dim: int = 2048,
        dropout: float = 0.1,
        max_seq_len: int = 64,
    ):
        super().__init__()
        self.embedding_dim = embedding_dim

        # Positional encoding
        self.pos_encoder = PositionalEncoding(embedding_dim, max_seq_len, dropout)

        # Transformer encoder
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=embedding_dim,
            nhead=num_heads,
            dim_feedforward=ff_dim,
            dropout=dropout,
            batch_first=True,
            activation="gelu",
        )
        self.transformer = nn.TransformerEncoder(
            encoder_layer, num_layers=num_layers,
        )

        # Temporal attention pooling
        self.pool = TemporalAttentionPooling(embedding_dim)

        # Anomaly head
        from research.models.anomaly_head import AnomalyHead
        self.anomaly_head = AnomalyHead(
            feature_dim=embedding_dim,
            dropout=dropout,
        )

        self._init_weights()
        logger.info(
            f"TemporalTransformer: dim={embedding_dim}, layers={num_layers}, "
            f"heads={num_heads}, ff={ff_dim}"
        )

    def _init_weights(self):
        """Xavier initialization for linear layers."""
        for p in self.parameters():
            if p.dim() > 1:
                nn.init.xavier_uniform_(p)

    def forward(self, x: torch.Tensor) -> Dict[str, torch.Tensor]:
        """Forward pass.

        Args:
            x: (batch, seq_len, embedding_dim) frame embedding sequence.

        Returns:
            Dict with:
                'anomaly_score': (batch,) anomaly scores in [0, 1]
                'attention_weights': (batch, seq_len) temporal attention
                'features': (batch, embedding_dim) pooled features
        """
        # Add positional encoding
        x = self.pos_encoder(x)

        # Transformer encoding
        encoded = self.transformer(x)  # (batch, seq_len, dim)

        # Temporal attention pooling
        pooled, attn_weights = self.pool(encoded)  # (batch, dim)

        # Anomaly classification
        result = self.anomaly_head(pooled)
        result["attention_weights"] = attn_weights
        return result

    def get_model_info(self) -> dict:
        total = sum(p.numel() for p in self.parameters())
        trainable = sum(p.numel() for p in self.parameters() if p.requires_grad)
        return {
            "model": "TemporalTransformer",
            "total_parameters": total,
            "trainable_parameters": trainable,
            "embedding_dim": self.embedding_dim,
        }


class TemporalTransformerVAD(nn.Module):
    """End-to-end Temporal Transformer VAD with CNN backbone.

    Architecture:
        (batch, seq_len, C, H, W) → CNN → embeddings → TemporalTransformer → score

    This makes it directly comparable to CNNLSTM which also takes raw frames.

    Args:
        backbone_name: timm CNN backbone.
        pretrained: Use pretrained backbone weights.
        embedding_dim: Feature dimension.
        num_layers: Transformer layers.
        num_heads: Attention heads.
        ff_dim: Feed-forward dimension.
        dropout: Dropout probability.
        max_seq_len: Maximum sequence length.
    """

    def __init__(
        self,
        backbone_name: str = "resnet18",
        pretrained: bool = True,
        embedding_dim: int = 512,
        num_layers: int = 4,
        num_heads: int = 8,
        ff_dim: int = 2048,
        dropout: float = 0.1,
        max_seq_len: int = 64,
    ):
        super().__init__()
        self.backbone_name = backbone_name
        self.embedding_dim = embedding_dim

        # CNN backbone
        try:
            import timm
            self.backbone = timm.create_model(
                backbone_name, pretrained=pretrained, num_classes=0,
            )
            with torch.no_grad():
                dummy = torch.randn(1, 3, 224, 224)
                backbone_dim = self.backbone(dummy).shape[-1]
        except ImportError:
            logger.warning("timm not available. Using simple CNN.")
            self.backbone = nn.Sequential(
                nn.Conv2d(3, 64, 7, stride=2, padding=3),
                nn.ReLU(inplace=True),
                nn.AdaptiveAvgPool2d(1),
                nn.Flatten(),
            )
            backbone_dim = 64

        self.projection = nn.Linear(backbone_dim, embedding_dim)

        # Temporal Transformer
        self.temporal_transformer = TemporalTransformer(
            embedding_dim=embedding_dim,
            num_layers=num_layers,
            num_heads=num_heads,
            ff_dim=ff_dim,
            dropout=dropout,
            max_seq_len=max_seq_len,
        )

        self._backbone_frozen = False

    def forward(self, x: torch.Tensor) -> Dict[str, torch.Tensor]:
        """Forward pass.

        Args:
            x: (batch, seq_len, C, H, W) video frames tensor.

        Returns:
            Dict with 'anomaly_score', 'attention_weights', 'features'.
        """
        batch_size, seq_len, C, H, W = x.shape

        # CNN per frame
        x = x.view(batch_size * seq_len, C, H, W)
        features = self.backbone(x)
        features = self.projection(features)
        features = features.view(batch_size, seq_len, self.embedding_dim)

        # Temporal Transformer
        return self.temporal_transformer(features)

    def freeze_backbone(self) -> None:
        for p in self.backbone.parameters():
            p.requires_grad = False
        self._backbone_frozen = True

    def unfreeze_backbone(self) -> None:
        for p in self.backbone.parameters():
            p.requires_grad = True
        self._backbone_frozen = False

    def get_model_info(self) -> dict:
        total = sum(p.numel() for p in self.parameters())
        trainable = sum(p.numel() for p in self.parameters() if p.requires_grad)
        return {
            "model": "TemporalTransformerVAD",
            "backbone": self.backbone_name,
            "total_parameters": total,
            "trainable_parameters": trainable,
            "backbone_frozen": self._backbone_frozen,
            "embedding_dim": self.embedding_dim,
        }
