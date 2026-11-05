# Privacy Policy

## System Privacy Notice

> **This system performs automated classroom video analysis using anonymous tracking identifiers. It does not perform facial identity recognition.**

## What This System Does

- Detects persons and mobile phones using YOLOv11 object detection
- Assigns anonymous tracking IDs (ST-001, ST-002, etc.) using ByteTrack
- Monitors student-phone spatial associations
- Analyzes temporal behavior patterns
- Generates alerts for potential unauthorized phone usage
- Captures evidence frames for review

## What This System Does NOT Do

- **No facial identity recognition** — The system cannot identify who a person is
- **No facial enrollment** — No face photos are collected or stored
- **No facial encoding/matching** — No face embeddings are computed
- **No biometric data** — No fingerprint, iris, or voice data
- **No identity tracking** — ST-001 is a temporary tracking ID, not a personal identifier

## Anonymous Tracking IDs

Each person detected receives an anonymous tracking ID:
- `ST-001`, `ST-002`, ... — Students (persons detected in video)
- `P-001`, `P-002`, ... — Phones (mobile phones detected in video)

These IDs are:
- Temporary (reset when the system restarts)
- Not linked to any personal identity
- Not stored with identifying information
- Generated sequentially by the tracker

## Data Storage

- **Video frames**: Processed in real-time, not stored permanently
- **Evidence frames**: Stored for configured retention period, then deleted
- **Alert records**: Stored in MongoDB with anonymous tracking IDs only
- **No personal data**: No names, photos, or identifiers are stored through the vision pipeline

## Compliance Notes

- Face recognition code has been archived under `archive/legacy_face_recognition/`
- Face recognition is disabled in configuration (`face_recognition.enabled: false`)
- Face recognition imports have been removed from the active pipeline
- The configuration does not allow re-enabling face recognition in the active pipeline

## Contact

For privacy concerns, contact the system administrator.
