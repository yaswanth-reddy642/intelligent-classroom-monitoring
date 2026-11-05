"""Score fusion — combines learned anomaly score with context/rule-based score.

Supports multiple fusion modes:
- weighted_average: configurable blend of learned and context scores
- max: take the maximum of both
- learned_only: use only the learned temporal model
- context_only: use only the existing context-aware rule-based score
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class FusionConfig:
    """Configuration for score fusion."""
    mode: str = "weighted_average"  # weighted_average, max, learned_only, context_only
    learned_weight: float = 0.5
    context_weight: float = 0.5


@dataclass
class FusionResult:
    """Result of score fusion."""
    final_score: float
    learned_score: Optional[float]
    context_score: float
    fusion_mode: str

    def to_dict(self) -> dict:
        return {
            "final_score": round(self.final_score, 4),
            "learned_score": round(self.learned_score, 4) if self.learned_score is not None else None,
            "context_score": round(self.context_score, 4),
            "fusion_mode": self.fusion_mode,
        }


class ScoreFusion:
    """Fuses learned temporal anomaly scores with rule-based context scores.

    The existing pipeline produces a context-aware anomaly score:
        A_context = w1*D + w2*S + w3*T + w4*C

    A learned temporal model (CNN-LSTM or Transformer) produces:
        A_learned = model.predict(sequence)

    Fusion combines both:
        A_final = f(A_learned, A_context)
    """

    def __init__(self, config: Optional[FusionConfig] = None):
        self._config = config or FusionConfig()
        logger.info(
            f"ScoreFusion initialized: mode={self._config.mode}, "
            f"learned_weight={self._config.learned_weight}, "
            f"context_weight={self._config.context_weight}"
        )

    def fuse(
        self,
        context_score: float,
        learned_score: Optional[float] = None,
    ) -> FusionResult:
        """Fuse learned and context scores.

        Args:
            context_score: Rule-based context-aware anomaly score [0, 1].
            learned_score: Learned temporal model score [0, 1], or None if disabled.

        Returns:
            FusionResult with the final combined score.
        """
        mode = self._config.mode

        if learned_score is None or mode == "context_only":
            return FusionResult(
                final_score=context_score,
                learned_score=learned_score,
                context_score=context_score,
                fusion_mode="context_only",
            )

        if mode == "learned_only":
            return FusionResult(
                final_score=learned_score,
                learned_score=learned_score,
                context_score=context_score,
                fusion_mode="learned_only",
            )

        if mode == "max":
            final = max(learned_score, context_score)
            return FusionResult(
                final_score=final,
                learned_score=learned_score,
                context_score=context_score,
                fusion_mode="max",
            )

        # Default: weighted_average
        w_l = self._config.learned_weight
        w_c = self._config.context_weight
        total_w = w_l + w_c
        if total_w > 0:
            final = (w_l * learned_score + w_c * context_score) / total_w
        else:
            final = context_score

        return FusionResult(
            final_score=max(0.0, min(1.0, final)),
            learned_score=learned_score,
            context_score=context_score,
            fusion_mode="weighted_average",
        )

    def update_config(self, config: FusionConfig) -> None:
        """Update fusion configuration at runtime."""
        self._config = config
        logger.info(f"ScoreFusion config updated: mode={config.mode}")
