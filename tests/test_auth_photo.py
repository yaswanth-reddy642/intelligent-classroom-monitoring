"""Test auth, photo upload, alerts on dashboard — complete flow."""
import sys, os, io
os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding="utf-8")
import requests, numpy as np

BASE = "http://localhost:8000"
P = F = 0

def test(name):
    def w(fn):
        global P, F
        try:
            fn()
            print(f"  [PASS] {name}")
            P += 1
        except Exception as e:
            print(f"  [FAIL] {name} -- {e}")
            F += 1
    return w

print("=" * 60)
print("  AUTH + PHOTO + DASHBOARD ALERTS TEST")
print("=" * 60)

# 1. Auth
print("\n--- Teacher Auth ---")
TOKEN = ""

@test("Register teacher")
def _():
    global TOKEN
    r = requests.post(f"{BASE}/api/auth/register", json={
        "name": "Dr. Priya Sharma",
        "email": "priya@college.edu",
        "password": "test1234",
        "department": "CSE",
        "employee_id": "EMP-001",
    })
    assert r.status_code == 200, f"{r.status_code}: {r.text}"
    d = r.json()
    assert d["token"]
    assert d["user"]["name"] == "Dr. Priya Sharma"
    TOKEN = d["token"]

@test("Login teacher")
def _():
    global TOKEN
    r = requests.post(f"{BASE}/api/auth/login", json={
        "email": "priya@college.edu",
        "password": "test1234",
    })
    assert r.status_code == 200
    TOKEN = r.json()["token"]

@test("Get current user (auth check)")
def _():
    r = requests.get(f"{BASE}/api/auth/me", headers={"Authorization": f"Bearer {TOKEN}"})
    assert r.status_code == 200
    assert r.json()["email"] == "priya@college.edu"

@test("Reject bad credentials")
def _():
    r = requests.post(f"{BASE}/api/auth/login", json={"email": "priya@college.edu", "password": "wrongpass"})
    assert r.status_code == 401

@test("Forgot password flow")
def _():
    r = requests.post(f"{BASE}/api/auth/forgot-password", json={"email": "priya@college.edu"})
    assert r.status_code == 200
    code = r.json().get("reset_code")
    assert code

    r2 = requests.post(f"{BASE}/api/auth/reset-password", json={
        "email": "priya@college.edu",
        "reset_code": code,
        "new_password": "newpass123",
    })
    assert r2.status_code == 200

    # Login with new password
    r3 = requests.post(f"{BASE}/api/auth/login", json={"email": "priya@college.edu", "password": "newpass123"})
    assert r3.status_code == 200

# 2. Student with photo
print("\n--- Student + Photo ---")

@test("Create student")
def _():
    r = requests.post(f"{BASE}/api/students", json={
        "name": "Ravi Kumar",
        "roll_number": "22TEST001",
        "department": "CSE",
        "section": "A",
        "semester": 5,
        "mobile_number": "9876543210",
    })
    assert r.status_code == 200

@test("Upload student photo")
def _():
    import cv2
    # Create a test image
    img = np.zeros((200, 200, 3), dtype=np.uint8)
    cv2.circle(img, (100, 80), 40, (200, 180, 160), -1)  # face shape
    cv2.circle(img, (85, 70), 5, (50, 50, 50), -1)  # eyes
    cv2.circle(img, (115, 70), 5, (50, 50, 50), -1)
    _, buf = cv2.imencode(".jpg", img)
    
    r = requests.post(
        f"{BASE}/api/students/22TEST001/photo",
        files={"file": ("ravi.jpg", io.BytesIO(buf.tobytes()), "image/jpeg")},
    )
    assert r.status_code == 200, f"{r.status_code}: {r.text}"
    assert r.json()["photo_url"].endswith(".jpg")
    print(f"    Photo URL: {r.json()['photo_url']}")

@test("Verify student has photo_url")
def _():
    r = requests.get(f"{BASE}/api/students/22TEST001")
    assert r.status_code == 200
    assert r.json()["photo_url"] != ""

# 3. Dashboard alerts
print("\n--- Dashboard Alerts ---")

@test("Create test alert for dashboard")
def _():
    r = requests.post(f"{BASE}/api/alerts/test", json={
        "student_display_id": "ST-001",
        "anomaly_score": 0.88,
        "phone_confidence": 0.95,
        "duration": 20.0,
        "context": "EXAM",
        "reasons": ["Phone usage during exam detected"],
    })
    assert r.status_code == 200

@test("Dashboard shows NEW alerts")
def _():
    r = requests.get(f"{BASE}/api/alerts", params={"status": "NEW", "limit": 5})
    assert r.status_code == 200
    alerts = r.json()["alerts"]
    assert len(alerts) > 0
    print(f"    New alerts: {len(alerts)}")

@test("Dashboard stats work")
def _():
    r = requests.get(f"{BASE}/api/stats/dashboard")
    assert r.status_code == 200

@test("Alert counts for dashboard")
def _():
    r = requests.get(f"{BASE}/api/alerts/count")
    assert r.status_code == 200
    d = r.json()
    assert d["total"] > 0

# Cleanup
print("\n--- Cleanup ---")

@test("Delete test student")
def _():
    r = requests.delete(f"{BASE}/api/students/22TEST001")
    assert r.status_code == 200

@test("Delete test teacher")
def _():
    from pymongo import MongoClient
    client = MongoClient("mongodb://localhost:27017")
    db = client["classroom_monitoring"]
    db.teachers.delete_one({"email": "priya@college.edu"})

@test("Delete test alerts")
def _():
    r = requests.get(f"{BASE}/api/alerts")
    for a in r.json().get("alerts", []):
        requests.delete(f"{BASE}/api/alerts/{a['alert_id']}")

print()
print("=" * 60)
print(f"  RESULT: {P} passed, {F} failed / {P+F} total")
if F == 0:
    print("  ALL TESTS PASSED!")
print("=" * 60)
