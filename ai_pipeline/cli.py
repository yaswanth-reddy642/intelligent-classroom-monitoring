"""CLI runner for the classroom monitoring pipeline.

Independently runnable — processes video and outputs results to terminal.
Optionally displays annotated video with OpenCV imshow.

Privacy: This system uses anonymous tracking IDs only.
No facial identity recognition is performed.

Usage:
    python -m ai_pipeline.cli --source video.mp4
    python -m ai_pipeline.cli --source webcam
    python -m ai_pipeline.cli --source video.mp4 --no-display
"""

import argparse
import logging
import signal
import sys
import time
from typing import Optional

import cv2
import numpy as np

from ai_pipeline.config import load_config, setup_logging, SystemConfig
from ai_pipeline.video.video_source import create_video_source
from ai_pipeline.pipeline import ClassroomMonitoringPipeline
from ai_pipeline.anomaly.models import AnomalyClassification

logger = logging.getLogger(__name__)

# Global flag for graceful shutdown
_shutdown = False


def _signal_handler(sig, frame):
    """Handle Ctrl+C for graceful shutdown."""
    global _shutdown
    _shutdown = True
    logger.info("Shutdown signal received. Stopping...")


def draw_annotations(
    frame: np.ndarray,
    result: dict,
) -> np.ndarray:
    """Draw bounding boxes and labels on the frame.

    Color coding:
    - Green: NORMAL
    - Yellow: SUSPICIOUS
    - Red: POTENTIAL_ANOMALY
    - Blue: Phones
    """
    annotated = frame.copy()

    # Color map
    colors = {
        "normal": (0, 200, 0),          # Green
        "active": (0, 200, 0),          # Green
        "suspicious": (0, 200, 255),    # Yellow
        "potential_phone_use": (0, 0, 255),  # Red
        "lost": (128, 128, 128),        # Gray
    }
    phone_color = (0, 140, 255)  # Bright Orange/Amber in BGR

    tracks = result.get("tracks", [])
    anomalies = result.get("anomalies", {})

    for track in tracks:
        x1, y1, x2, y2 = [int(v) for v in track.bbox]

        if track.class_name == "mobile_phone":
            # Multi-angle & concealed orientation detection
            pw = max(1, x2 - x1)
            ph = max(1, y2 - y1)
            is_concealed = getattr(track, 'is_concealed', False)
            if is_concealed:
                orient = "CONCEALED"
            elif pw > 1.35 * ph:
                orient = "LANDSCAPE"
            elif ph > 1.35 * pw:
                orient = "PORTRAIT"
            else:
                orient = "ANGLED"
            conf_val = getattr(track, 'confidence', 0.0)
            conf_pct = int(conf_val * 100) if conf_val > 0 else 0

            # Draw phone with bright visible border and tag
            cv2.rectangle(annotated, (x1, y1), (x2, y2), phone_color, 2)
            tag = f"PHONE {conf_pct}% [{orient}]" if conf_pct > 0 else f"PHONE [{orient}]"
            (tw, th), _ = cv2.getTextSize(tag, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
            cv2.rectangle(annotated, (x1, max(0, y1 - th - 6)), (x1 + tw + 4, y1), phone_color, -1)
            cv2.putText(
                annotated, tag,
                (x1 + 2, max(th, y1 - 3)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1, cv2.LINE_AA,
            )
        else:
            # Draw student bounding box
            is_phone_use = (track.state.value == "potential_phone_use")
            color = (0, 0, 255) if is_phone_use else colors.get(track.state.value, (0, 200, 0))
            thickness = 3 if is_phone_use else 2
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, thickness)

            # Student name & roll number label banner
            stu_name = getattr(track, "student_name", None)
            roll_no = getattr(track, "roll_number", None)
            is_unknown = getattr(track, "is_unknown", False) or (roll_no in (None, "UNKNOWN", "N/A") or stu_name in ("Unknown Person", "Unknown"))

            m_conf = getattr(track, "match_confidence", 0.0)
            if is_unknown:
                display_label = f"Unknown Person ({track.display_id})"
            elif stu_name and roll_no and roll_no not in ("UNKNOWN", "N/A"):
                if m_conf and m_conf > 0:
                    display_label = f"{stu_name} ({roll_no}) [{int(m_conf)}%]"
                else:
                    display_label = f"{stu_name} ({roll_no})"
            else:
                display_label = f"Unknown Person ({track.display_id})"

            label = f"PHONE USE: {display_label}" if is_phone_use else display_label
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
            cv2.rectangle(annotated, (x1, max(0, y1 - th - 8)), (x1 + tw + 6, y1), color, -1)
            cv2.putText(
                annotated, label,
                (x1 + 3, max(th, y1 - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA,
            )

            # Anomaly score if available
            anomaly = anomalies.get(track.tracking_id)
            if anomaly and anomaly.score > 0:
                score_text = f"Score: {anomaly.score:.2f} [{anomaly.classification.value}]"
                cv2.putText(
                    annotated, score_text,
                    (x1, y2 + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA,
                )

    # Draw connection lines between associated student and phone
    assoc_result = result.get("associations")
    if assoc_result and hasattr(assoc_result, "associations"):
        for a in assoc_result.associations:
            s_track = next((t for t in tracks if t.tracking_id == a.student_tracking_id), None)
            p_track = next((t for t in tracks if t.tracking_id == a.phone_tracking_id), None)
            if s_track and p_track:
                sc = (int(s_track.center[0]), int(s_track.center[1]))
                pc = (int(p_track.center[0]), int(p_track.center[1]))
                cv2.line(annotated, sc, pc, (0, 0, 255), 2, cv2.LINE_AA)

    # Context and stats overlay
    context = result.get("context")
    if context:
        ctx_text = f"Context: {context.mode.value}"
        cv2.putText(
            annotated, ctx_text,
            (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2,
        )

    stats_text = (
        f"Students: {result.get('student_count', 0)} | "
        f"Phones: {result.get('phone_count', 0)} | "
        f"Frame: {result.get('frame_id', 0)}"
    )
    cv2.putText(
        annotated, stats_text,
        (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1,
    )

    return annotated


def run_pipeline(config: SystemConfig, display: bool = True) -> None:
    """Run the full pipeline on the configured video source.

    Args:
        config: System configuration.
        display: Whether to show annotated video window.
    """
    global _shutdown

    # Create video source
    video = create_video_source(config.video)
    if not video.start():
        logger.error("Failed to start video source. Exiting.")
        return

    # Create pipeline
    pipeline = ClassroomMonitoringPipeline(config)

    logger.info(
        f"Pipeline started. Source: {config.video.source_type} "
        f"({config.video.source_path})"
    )
    logger.info(f"Tracking: Anonymous IDs (ST-XXX)")
    logger.info(f"Context: {config.context.default_mode}")
    logger.info("Press Ctrl+C to stop.\n")

    frame_count = 0
    start_time = time.time()

    try:
        while not _shutdown:
            frame = video.read_frame()
            if frame is None:
                if video.get_frame_count() > 0:
                    # End of file
                    logger.info("End of video file reached.")
                    break
                else:
                    # Live source temporary failure
                    time.sleep(0.01)
                    continue

            # Process frame
            result = pipeline.process_frame(frame)
            frame_count += 1

            # Print results periodically
            detections = result["detections"]
            if frame_count % 30 == 0 or result.get("alerts"):
                elapsed = time.time() - start_time
                fps = frame_count / max(elapsed, 1)

                print(
                    f"\r[Frame {result['frame_id']:05d}] "
                    f"Students: {result['student_count']} | "
                    f"Phones: {result['phone_count']} | "
                    f"Inference: {detections.inference_time_ms:.1f}ms | "
                    f"FPS: {fps:.1f}",
                    end="",
                )

            # Print alerts
            for alert in result.get("alerts", []):
                print(
                    f"\n{'=' * 60}"
                    f"\n⚠️  ALERT: {alert.event_type}"
                    f"\n   Tracking ID: {alert.student_display_id}"
                    f"\n   Score:   {alert.anomaly_score:.2f}"
                    f"\n   Duration: {alert.duration:.1f}s"
                    f"\n   Context: {alert.context}"
                    f"\n   Reasons: {', '.join(alert.reasons)}"
                    f"\n{'=' * 60}"
                )

            # Display annotated frame
            if display:
                annotated = draw_annotations(frame, result)
                cv2.imshow("Classroom Monitor", annotated)
                key = cv2.waitKey(1) & 0xFF
                if key == ord("q"):
                    break
                elif key == ord("e"):
                    pipeline.set_context("EXAM")
                    print("\n[Context changed to EXAM]")
                elif key == ord("l"):
                    pipeline.set_context("LECTURE")
                    print("\n[Context changed to LECTURE]")
                elif key == ord("b"):
                    pipeline.set_context("BREAK")
                    print("\n[Context changed to BREAK]")

    except KeyboardInterrupt:
        logger.info("Interrupted by user.")
    finally:
        video.stop()
        if display:
            cv2.destroyAllWindows()

        elapsed = time.time() - start_time
        fps = frame_count / max(elapsed, 1)
        print(
            f"\n\nPipeline stopped. Processed {frame_count} frames "
            f"in {elapsed:.1f}s ({fps:.1f} FPS)"
        )
        print(f"Total alerts generated: {pipeline.alert_engine.alert_count}")


def main():
    """CLI entry point."""
    signal.signal(signal.SIGINT, _signal_handler)

    parser = argparse.ArgumentParser(
        description="Intelligent Classroom Monitoring - AI Pipeline CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m ai_pipeline.cli --source video.mp4
  python -m ai_pipeline.cli --source webcam
  python -m ai_pipeline.cli --source rtsp://192.168.1.100/stream

Keyboard shortcuts (in display window):
  q - Quit
  e - Switch to EXAM mode
  l - Switch to LECTURE mode
  b - Switch to BREAK mode
        """,
    )
    parser.add_argument(
        "--source", type=str, default="webcam",
        help="Video source: 'webcam', file path, or RTSP URL",
    )
    parser.add_argument(
        "--config", type=str, default=None,
        help="Path to config YAML file",
    )
    parser.add_argument(
        "--no-display", action="store_true",
        help="Disable video display window",
    )
    parser.add_argument(
        "--context", type=str, default=None,
        choices=["LECTURE", "EXAM", "BREAK", "AUTHORIZED_PHONE_ACTIVITY"],
        help="Initial classroom context mode",
    )
    parser.add_argument(
        "--device", type=str, default=None,
        help="Inference device (auto, cpu, cuda)",
    )

    args = parser.parse_args()

    # Load config
    config = load_config(args.config)
    setup_logging(config.logging)

    # Apply CLI overrides
    source = args.source.lower()
    if source == "webcam":
        config.video.source_type = "webcam"
        config.video.source_path = "0"
    elif source.startswith("rtsp://"):
        config.video.source_type = "rtsp"
        config.video.source_path = args.source
    else:
        config.video.source_type = "file"
        config.video.source_path = args.source

    if args.context:
        config.context.default_mode = args.context

    if args.device:
        config.detection.device = args.device

    # Print banner with privacy notice
    print("=" * 60)
    print("  Intelligent Classroom Monitoring System")
    print("  YOLOv11 + Anonymous Tracking + Anomaly Detection")
    print("=" * 60)
    print(f"  Source:     {config.video.source_type} ({config.video.source_path})")
    print(f"  Model:      {config.detection.model_path}")
    print(f"  Device:     {config.detection.device}")
    print(f"  Tracking:   Anonymous IDs (ST-XXX)")
    print(f"  Context:    {config.context.default_mode}")
    print(f"  Display:    {'Yes' if not args.no_display else 'No'}")
    print("=" * 60)
    print("  PRIVACY: No facial identity recognition is performed.")
    print("=" * 60)
    print()

    # Run
    run_pipeline(config, display=not args.no_display)


if __name__ == "__main__":
    main()
