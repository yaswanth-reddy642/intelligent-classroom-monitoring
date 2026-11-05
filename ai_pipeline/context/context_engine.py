"""Classroom context engine.

Manages classroom operating modes (LECTURE, EXAM, etc.) and provides
context multipliers that affect anomaly scoring. Teachers/admins
can change the mode at runtime via the API.
"""

import logging
from ai_pipeline.config import ContextConfig
from ai_pipeline.context.models import ContextMode, ClassroomContext

logger = logging.getLogger(__name__)


class ContextEngine:
    """Manages classroom context and provides scoring multipliers.

    Modes and their effects:
    - EXAM: High multiplier — phones are very suspicious
    - LECTURE: Standard multiplier
    - AUTHORIZED_PHONE_ACTIVITY: Near-zero — suppress alerts
    - BREAK: Low multiplier — configurable suppression
    """

    def __init__(self, config: ContextConfig):
        self._config = config
        self._mode = ContextMode(config.default_mode)
        self._multipliers = config.mode_multipliers
        logger.info(f"Context engine initialized: mode={self._mode.value}")

    def set_mode(self, mode: str) -> bool:
        """Set the classroom mode.

        Args:
            mode: Mode string ('LECTURE', 'EXAM', etc.)

        Returns:
            True if mode was set successfully.
        """
        try:
            self._mode = ContextMode(mode.upper())
            logger.info(f"Classroom context changed to: {self._mode.value}")
            return True
        except ValueError:
            logger.warning(f"Invalid context mode: {mode}")
            return False

    def get_context(self) -> ClassroomContext:
        """Get the current classroom context with multiplier."""
        multiplier = self._multipliers.get(self._mode.value, 1.0)
        suppress = self._mode in (
            ContextMode.AUTHORIZED_PHONE_ACTIVITY,
            ContextMode.BREAK,
        )
        return ClassroomContext(
            mode=self._mode,
            multiplier=multiplier,
            suppress_alerts=suppress and multiplier < 0.3,
        )

    def get_multiplier(self) -> float:
        """Get the current context multiplier for anomaly scoring."""
        return self._multipliers.get(self._mode.value, 1.0)

    @property
    def current_mode(self) -> ContextMode:
        return self._mode

    @property
    def current_mode_str(self) -> str:
        return self._mode.value
