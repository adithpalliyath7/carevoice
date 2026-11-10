from datetime import date, timedelta, datetime, timezone
from fastapi.testclient import TestClient
from app.main import app
from app.data import generate_slots
from app import waitlist as wl

client = TestClient(app)
DAY = (date.today() + timedelta(days=1)).isoformat()


def _book(doctor_id, phone):
    slot = next(s["time"] for s in generate_slots(doctor_id, date.fromisoformat(DAY)) if s["available"])
    r = client.post("/api/appointments", json={"doctor_id": doctor_id, "date": DAY, "time": slot,
                   "patient_name": "Holder", "patient_phone": phone, "confirmed": True})
    assert r.status_code == 200, r.text
    return r.json()["token"], slot


def test_join_and_cancel_triggers_offer():
    token, slot = _book("dr-nisha-gupta", "1111111111")
    j = client.post("/api/waitlist", json={"doctor_id": "dr-nisha-gupta", "date": DAY,
                    "preferred_time": slot, "patient_name": "Waiter", "phone": "2222222222"})
    assert j.status_code == 200
    wid = j.json()["id"]
    assert j.json()["status"] == "waiting"
    cc = client.post(f"/api/appointments/{token}/cancel", json={"reason": "Cannot come", "by": "patient"})
    assert cc.status_code == 200
    got = client.get(f"/api/waitlist/{wid}")
    assert got.json()["status"] == "offered"
    assert got.json()["offer"]["time"] == slot


def test_accept_requires_confirmation_then_books():
    token, slot = _book("dr-farhan-ali", "3333333333")
    j = client.post("/api/waitlist", json={"doctor_id": "dr-farhan-ali", "date": DAY,
                    "preferred_time": slot, "patient_name": "Waiter2", "phone": "4444444444"})
    wid = j.json()["id"]
    client.post(f"/api/appointments/{token}/cancel", json={"reason": "x", "by": "patient"})
    # Not confirmed -> 422, nothing booked
    r = client.post(f"/api/waitlist/{wid}/accept", json={"confirmed": False})
    assert r.status_code == 422
    assert r.json()["detail"] == "confirmation_required"
    # Confirmed -> booked with a real token
    r2 = client.post(f"/api/waitlist/{wid}/accept", json={"confirmed": True})
    assert r2.status_code == 201, r2.text
    assert r2.json()["token"].startswith("CV-")
    assert client.get(f"/api/waitlist/{wid}").json()["status"] == "accepted"


def test_decline_passes_offer_to_next():
    token, slot = _book("dr-kavya-shetty", "5555555555")
    w1 = client.post("/api/waitlist", json={"doctor_id": "dr-kavya-shetty", "date": DAY,
                     "preferred_time": slot, "patient_name": "First", "phone": "6666666666"}).json()
    w2 = client.post("/api/waitlist", json={"doctor_id": "dr-kavya-shetty", "date": DAY,
                     "preferred_time": slot, "patient_name": "Second", "phone": "7777777777"}).json()
    client.post(f"/api/appointments/{token}/cancel", json={"reason": "x", "by": "patient"})
    assert client.get(f"/api/waitlist/{w1['id']}").json()["status"] == "offered"
    d = client.post(f"/api/waitlist/{w1['id']}/decline")
    assert d.status_code == 200
    assert client.get(f"/api/waitlist/{w2['id']}").json()["status"] == "offered"


def test_stale_offer_expires_and_rolls_forward():
    token, slot = _book("dr-vikram-reddy", "8888888888")
    w1 = client.post("/api/waitlist", json={"doctor_id": "dr-vikram-reddy", "date": DAY,
                     "preferred_time": slot, "patient_name": "First", "phone": "9999999990"}).json()
    w2 = client.post("/api/waitlist", json={"doctor_id": "dr-vikram-reddy", "date": DAY,
                     "preferred_time": slot, "patient_name": "Second", "phone": "9999999991"}).json()
    client.post(f"/api/appointments/{token}/cancel", json={"reason": "x", "by": "patient"})
    # Force the offer to expire
    entry = next(e for e in wl.WAITLIST if e["id"] == w1["id"])
    past = (datetime.now(timezone.utc) - timedelta(minutes=31)).isoformat()
    entry["offer"]["expires_at"] = past
    got = client.get(f"/api/waitlist/{w1['id']}")
    assert got.json()["status"] == "expired"
    assert client.get(f"/api/waitlist/{w2['id']}").json()["status"] == "offered"


def test_staff_waitlist_list_guarded():
    r = client.get("/api/ops/waitlist", headers={"X-Demo-Role": "patient"})
    assert r.status_code == 403
    r2 = client.get("/api/ops/waitlist", headers={"X-Demo-Role": "receptionist"})
    assert r2.status_code == 200
    assert "waitlist" in r2.json()


def test_senior_mode_lowers_tts_speed():
    from app.gnani import effective_speed
    assert effective_speed(1.15, senior_mode=True) == 0.85
    assert effective_speed(1.0, senior_mode=False) == 1.0
    assert effective_speed(1.0, senior_mode=True) == 0.85
