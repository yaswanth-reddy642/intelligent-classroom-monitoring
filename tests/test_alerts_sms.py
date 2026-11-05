"""Test alerts, SMS notifications, and student enrollment with mobile numbers."""
import sys, os
os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding="utf-8")

import requests

BASE = "http://localhost:8000"
P = 0
F = 0

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
print("  ALERTS + SMS + ENROLLMENT TEST")
print("=" * 60)

# 1. Enroll students with mobile numbers
print("\n--- Student Enrollment ---")

@test("Create student with mobile number")
def _():
    r = requests.post(f"{BASE}/api/students", json={
        "name": "Ravi Kumar",
        "roll_number": "22B01A001",
        "department": "CSE",
        "section": "A",
        "semester": 5,
        "mobile_number": "9876543210",
        "parent_mobile": "9876543211",
        "email": "ravi@college.edu"
    })
    assert r.status_code == 200, f"Status: {r.status_code}"
    d = r.json()
    assert d["student_id"].startswith("STU-")
    assert d["name"] == "Ravi Kumar"

@test("Create second student")
def _():
    r = requests.post(f"{BASE}/api/students", json={
        "name": "Priya Sharma",
        "roll_number": "22B01A002",
        "department": "CSE",
        "section": "A",
        "semester": 5,
        "mobile_number": "9123456789",
        "parent_mobile": "",
        "email": ""
    })
    assert r.status_code == 200

@test("Verify students have mobile numbers")
def _():
    r = requests.get(f"{BASE}/api/students")
    students = r.json()["students"]
    ravi = next((s for s in students if s["roll_number"] == "22B01A001"), None)
    assert ravi is not None, "Ravi not found"
    assert ravi["mobile_number"] == "9876543210"
    assert ravi["parent_mobile"] == "9876543211"
    assert ravi["email"] == "ravi@college.edu"

# 2. Test alert creation + SMS
print("\n--- Alert Creation + SMS ---")

@test("Create test alert and send SMS")
def _():
    r = requests.post(f"{BASE}/api/alerts/test", json={
        "student_display_id": "ST-001",
        "anomaly_score": 0.85,
        "phone_confidence": 0.92,
        "duration": 15.0,
        "context": "LECTURE",
        "reasons": ["Phone detected near student for extended period"]
    })
    assert r.status_code == 200, f"Status: {r.status_code} {r.text}"
    d = r.json()
    assert "alert" in d
    assert d["alert"]["status"] == "NEW"
    assert d["alert"]["anomaly_score"] == 0.85
    sms = d.get("sms_notifications", [])
    print(f"    SMS notifications: {len(sms)} processed")
    for s in sms:
        print(f"      -> {s.get('student', '?')}: {s.get('result', {}).get('status', '?')}")

@test("List alerts shows the test alert")
def _():
    r = requests.get(f"{BASE}/api/alerts")
    assert r.status_code == 200
    d = r.json()
    assert d["total"] > 0
    assert len(d["alerts"]) > 0
    a = d["alerts"][0]
    assert a["status"] == "NEW"

@test("Get alert counts")
def _():
    r = requests.get(f"{BASE}/api/alerts/count")
    assert r.status_code == 200
    d = r.json()
    assert d["total"] > 0
    assert d["new"] > 0
    print(f"    Counts: total={d['total']} new={d['new']} ack={d['acknowledged']} resolved={d['resolved']}")

# 3. Alert status management
print("\n--- Alert Status Management ---")

@test("Acknowledge alert")
def _():
    r = requests.get(f"{BASE}/api/alerts", params={"status": "NEW"})
    alerts = r.json()["alerts"]
    assert len(alerts) > 0
    aid = alerts[0]["alert_id"]
    r2 = requests.patch(f"{BASE}/api/alerts/{aid}/status", json={"status": "ACKNOWLEDGED"})
    assert r2.status_code == 200
    assert r2.json()["status"] == "ACKNOWLEDGED"

@test("Resolve alert")
def _():
    r = requests.get(f"{BASE}/api/alerts", params={"status": "ACKNOWLEDGED"})
    alerts = r.json()["alerts"]
    assert len(alerts) > 0
    aid = alerts[0]["alert_id"]
    r2 = requests.patch(f"{BASE}/api/alerts/{aid}/status", json={"status": "RESOLVED"})
    assert r2.status_code == 200

@test("Send SMS for specific alert")
def _():
    r = requests.get(f"{BASE}/api/alerts")
    alerts = r.json()["alerts"]
    assert len(alerts) > 0
    aid = alerts[0]["alert_id"]
    r2 = requests.post(f"{BASE}/api/alerts/{aid}/send-sms")
    assert r2.status_code == 200
    d = r2.json()
    print(f"    SMS count: {d.get('count', 0)}")

# 4. Alert filter
print("\n--- Alert Filtering ---")

@test("Filter by NEW status")
def _():
    r = requests.get(f"{BASE}/api/alerts", params={"status": "NEW"})
    assert r.status_code == 200

@test("Filter by RESOLVED status")
def _():
    r = requests.get(f"{BASE}/api/alerts", params={"status": "RESOLVED"})
    assert r.status_code == 200
    assert r.json()["total"] >= 1

# 5. Delete
print("\n--- Cleanup ---")

@test("Delete an alert")
def _():
    r = requests.get(f"{BASE}/api/alerts")
    alerts = r.json()["alerts"]
    if alerts:
        aid = alerts[0]["alert_id"]
        r2 = requests.delete(f"{BASE}/api/alerts/{aid}")
        assert r2.status_code == 200

@test("Delete test students")
def _():
    r1 = requests.delete(f"{BASE}/api/students/22B01A001")
    r2 = requests.delete(f"{BASE}/api/students/22B01A002")
    assert r1.status_code == 200
    assert r2.status_code == 200

print()
print("=" * 60)
print(f"  RESULT: {P} passed, {F} failed / {P+F} total")
if F == 0:
    print("  ALL TESTS PASSED!")
print("=" * 60)
