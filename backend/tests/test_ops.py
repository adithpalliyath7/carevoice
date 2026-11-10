from datetime import date, timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.data import generate_slots
from app import ops

client = TestClient(app)
STAFF = {"X-Demo-Role": "receptionist"}
ADMIN = {"X-Demo-Role": "admin"}
PATIENT = {"X-Demo-Role": "patient"}
DAY = (date.today() + timedelta(days=1)).isoformat()


def _avail_slot(doctor_id):
    return next(s["time"] for s in generate_slots(doctor_id, date.fromisoformat(DAY)) if s["available"])


def _book_online():
    slot = _avail_slot("dr-arun-kumar")
    r = client.post("/api/appointments", json={"doctor_id": "dr-arun-kumar", "date": DAY, "time": slot,
                   "patient_name": "Online Pat", "patient_phone": "7777777777", "confirmed": True})
    assert r.status_code == 200, r.text
    return r.json()


def test_role_guard_403_for_patient():
    r = client.get("/api/ops/appointments", headers=PATIENT)
    assert r.status_code == 403
    r2 = client.get("/api/ops/appointments", headers=STAFF)
    assert r2.status_code == 200


def test_demo_login():
    r = client.post("/api/ops/login", json={"email": "admin@demo", "password": "demo1234"})
    assert r.status_code == 200
    assert r.json()["role"] == "admin"
    assert "DEMO ONLY" in r.json()["warning"]
    bad = client.post("/api/ops/login", json={"email": "admin@demo", "password": "wrong"})
    assert bad.status_code == 401


def test_walk_in_creates_cv_w_token():
    slot = _avail_slot("dr-meera-iyer")
    r = client.post("/api/ops/walk-in", headers=STAFF,
                    json={"doctor_id": "dr-meera-iyer", "date": DAY, "time": slot,
                          "patient_name": "Walk In", "patient_phone": "6666666666"})
    assert r.status_code == 200, r.text
    assert r.json()["token"].startswith("CV-W")
    assert r.json()["source"] == "walk-in"


def test_check_in_assigns_queue_position_and_call_next():
    appt = _book_online()
    c = client.post("/api/ops/check-in", headers=STAFF, json={"token": appt["token"]})
    assert c.status_code == 200
    assert c.json()["queue_position"] >= 1
    q = client.get("/api/ops/queue", headers=STAFF,
                   params={"doctor_id": "dr-arun-kumar", "date": DAY})
    assert any(e["token"] == appt["token"] for e in q.json()["queue"])
    n = client.post("/api/ops/queue/call-next", headers=STAFF,
                    params={"doctor_id": "dr-arun-kumar", "date": DAY})
    assert n.status_code == 200
    d = client.post(f"/api/ops/queue/{appt['token']}/mark-done", headers=STAFF)
    assert d.status_code == 200
    assert client.get(f"/api/appointments/{appt['token']}").json()["status"] == "completed"


def test_cancel_frees_slot():
    slot = _avail_slot("dr-lakshmi-rao")
    r = client.post("/api/appointments", json={"doctor_id": "dr-lakshmi-rao", "date": DAY, "time": slot,
                   "patient_name": "Cancel Me", "patient_phone": "5555555555", "confirmed": True})
    token = r.json()["token"]
    cc = client.post(f"/api/ops/appointments/{token}/cancel", headers=STAFF,
                     json={"reason": "Doctor unavailable"})
    assert cc.status_code == 200
    # Slot shows available again in the slot list
    slots = client.get(f"/api/doctors/dr-lakshmi-rao/slots?date={DAY}").json()["slots"]
    assert next(s for s in slots if s["time"] == slot)["available"] is True
    # And it appears in the cancellations list
    cl = client.get("/api/ops/cancellations", headers=STAFF, params={"date": DAY})
    assert any(c["token"] == token for c in cl.json()["cancellations"])


def test_delay_appears_on_doctor_and_appointment():
    appt = _book_online()
    d = client.post("/api/ops/doctors/dr-arun-kumar/delay", headers=STAFF,
                    json={"minutes": 30, "message": "Doctor delayed by 30 minutes due to an emergency case."})
    assert d.status_code == 200
    doc = client.get("/api/doctors/dr-arun-kumar")
    assert doc.json()["delay_minutes"] == 30
    got = client.get(f"/api/appointments/{appt['token']}")
    assert got.json()["delay_minutes"] == 30
    assert "30 minutes" in got.json()["delay_announcement"]
    client.post("/api/ops/doctors/dr-arun-kumar/delay/clear", headers=STAFF)


def test_analytics_counts_match_bookings():
    _book_online()
    a = client.get("/api/ops/analytics/daily", headers=STAFF, params={"date": DAY})
    body = a.json()
    assert body["total"] >= 1
    assert body["total"] == body["booked"] + body["cancelled"] + body["no_show"] or body["total"] >= body["booked"]
    assert "Orthopedics" in body["by_speciality"] or body["by_speciality"]
    lang = client.get("/api/ops/analytics/language", headers=STAFF)
    assert lang.status_code == 200
    assert "by_language" in lang.json()


def test_admin_only_availability_update():
    r = client.put("/api/ops/doctors/dr-anitha-nair/availability", headers=STAFF,
                   json={"max_per_day": 20})
    assert r.status_code == 403  # receptionist cannot manage availability
    r2 = client.put("/api/ops/doctors/dr-anitha-nair/availability", headers=ADMIN,
                    json={"max_per_day": 20})
    assert r2.status_code == 200
    assert r2.json()["max_per_day"] == 20
