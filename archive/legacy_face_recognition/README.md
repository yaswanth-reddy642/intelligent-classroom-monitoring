# Legacy Face Recognition Module

> **ARCHIVED** — This module has been removed from the active pipeline for privacy reasons.

This directory contains the original face recognition implementation for historical reference only. These files are NOT used by the active application.

The active system uses anonymous tracking IDs (ST-001, ST-002, etc.) with no facial identity recognition.

## Archived Files

- `__init__.py` — Module init
- `enrollment.py` — Student photo enrollment
- `face_database.py` — Face embedding storage
- `face_detector.py` — Face detection (InsightFace)
- `face_encoder.py` — Face embedding extraction
- `face_matcher.py` — Cosine similarity matching
- `models.py` — Data models for face recognition
- `recognition_engine.py` — Main face recognition engine

## Why Archived

The system privacy policy prohibits facial identity recognition. See `docs/PRIVACY.md`.
