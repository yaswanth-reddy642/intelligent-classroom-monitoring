"""Temporal anomaly localization — re-exported from __init__.py.

See research/temporal/__init__.py for the full TemporalLocalizer implementation.
This file serves as an additional import point.
"""

from research.temporal import TemporalLocalizer, AnomalySegment, LocalizationResult

__all__ = ["TemporalLocalizer", "AnomalySegment", "LocalizationResult"]
