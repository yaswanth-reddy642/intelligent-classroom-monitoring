# Anomaly Schema

This document defines the schema for anomalies in the Intelligent Classroom Monitoring project.

## Labels
- **NORMAL (0)**: Routine classroom activities.
- **POTENTIAL_PHONE_USAGE (1)**: Detection of a phone or phone-like interaction.
- **AUTHORIZED_PHONE_ACTIVITY (2)**: Phone usage allowed by context (e.g. during specific breaks).
- **AMBIGUOUS (3)**: Unclear actions that require human verification.
- **OTHER_ANOMALY (4)**: General anomalies (cheating, leaving mid-exam, fighting).

## Transformation Notes for Benchmark Datasets
When evaluating on generic datasets (ShanghaiTech, UCSD Ped2, UCF-Crime):
- Generic anomalies map to **OTHER_ANOMALY (4)**.
- For evaluating purely phone usage, generic datasets are filtered or ignored.
