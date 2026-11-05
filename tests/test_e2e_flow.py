"""Test the complete video upload + processing + WebSocket flow."""
import sys, os, time, json, tempfile
os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding="utf-8")

import requests
import numpy as np
import cv2

BASE = "http://localhost:8000"

print("=" * 60)
print("  END-TO-END VIDEO FLOW TEST")
print("=" * 60)

# Step 1: Create a real test video with colored frames
print("\n[1] Creating test video with detectable content...")
temp_video = os.path.join(tempfile.gettempdir(), "test_classroom.mp4")
fourcc = cv2.VideoWriter_fourcc(*"mp4v")
writer = cv2.VideoWriter(temp_video, fourcc, 15.0, (640, 480))
for i in range(45):  # 3 seconds at 15fps
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    # Draw a rectangle (simulates a person shape)
    cv2.rectangle(frame, (200, 100), (350, 400), (0, 255, 0), -1)
    # Draw a small rectangle (simulates a phone)
    cv2.rectangle(frame, (280, 250), (320, 300), (255, 0, 0), -1)
    cv2.putText(frame, f"Frame {i}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    writer.write(frame)
writer.release()
file_size = os.path.getsize(temp_video)
print(f"  Created: {temp_video} ({file_size / 1024:.1f} KB, 45 frames)")

# Step 2: Upload the video
print("\n[2] Uploading video to backend...")
with open(temp_video, "rb") as f:
    r = requests.post(f"{BASE}/api/detection/upload-video", files={"file": ("test_classroom.mp4", f, "video/mp4")})
assert r.status_code == 200, f"Upload failed: {r.status_code} {r.text}"
upload_result = r.json()
video_path = upload_result["path"]
print(f"  Uploaded: {upload_result['filename']} -> {video_path} ({upload_result['size_mb']} MB)")

# Step 3: Start detection with uploaded video
print("\n[3] Starting detection pipeline with uploaded video...")
r = requests.post(f"{BASE}/api/detection/start", json={"source": video_path})
assert r.status_code == 200, f"Start failed: {r.status_code} {r.text}"
print(f"  Result: {r.json()}")

# Step 4: Wait and check status
time.sleep(2)
r = requests.get(f"{BASE}/api/detection/status")
status = r.json()
print(f"\n[4] Detection status: running={status['running']}, fps={status['fps']}")

# Step 5: Try to get an annotated frame
print("\n[5] Getting annotated frame...")
r = requests.get(f"{BASE}/api/detection/frame")
if r.status_code == 200:
    frame_data = r.json()
    b64_len = len(frame_data.get("frame", ""))
    print(f"  Got frame: {b64_len} bytes base64")
else:
    print(f"  Frame not ready: {r.status_code}")

# Step 6: Get current detections
print("\n[6] Getting current detections...")
r = requests.get(f"{BASE}/api/detection/current")
det = r.json()
print(f"  Running: {det.get('running')}")
print(f"  Students: {det.get('student_count', 0)}")
print(f"  Phones: {det.get('phone_count', 0)}")
print(f"  Tracks: {len(det.get('tracks', []))}")

# Step 7: Test WebSocket connection
print("\n[7] Testing WebSocket connection...")
try:
    import websockets
    import asyncio

    async def test_ws():
        frames_received = 0
        async with websockets.connect("ws://localhost:8000/ws/live") as ws:
            for _ in range(5):  # Try to get 5 messages
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=3)
                    data = json.loads(msg)
                    if data.get("type") == "frame" and data.get("frame"):
                        frames_received += 1
                        stats = data.get("stats", {})
                        print(f"  WS frame: students={stats.get('student_count', 0)} phones={stats.get('phone_count', 0)} fps={stats.get('fps', 0)}")
                except asyncio.TimeoutError:
                    break
        return frames_received

    frames = asyncio.run(test_ws())
    print(f"  Received {frames} frames via WebSocket")
except Exception as e:
    print(f"  WebSocket test error: {e}")

# Step 8: Stop detection
print("\n[8] Stopping detection...")
r = requests.post(f"{BASE}/api/detection/stop")
print(f"  Result: {r.json()}")

# Step 9: Test student enrollment
print("\n[9] Testing student enrollment...")
r = requests.post(f"{BASE}/api/students", json={
    "name": "Test Student",
    "roll_number": "TEST-E2E-001",
    "department": "Computer Science",
    "section": "A",
    "semester": 5
})
print(f"  Create: {r.status_code} {r.json()}")

r = requests.get(f"{BASE}/api/students")
students = r.json()
found = any(s.get("roll_number") == "TEST-E2E-001" for s in students.get("students", []))
print(f"  Found in list: {found}")

r = requests.delete(f"{BASE}/api/students/TEST-E2E-001")
print(f"  Delete: {r.status_code} {r.json()}")

# Cleanup
os.unlink(temp_video)

print("\n" + "=" * 60)
print("  END-TO-END TEST COMPLETE")
print("=" * 60)
