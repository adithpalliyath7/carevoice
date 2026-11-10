from datetime import date, timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.data import generate_slots

client = TestClient(app)
DAY = (date.today() + timedelta(days=1)).isoformat()

def _available_slot(doctor_id):
    return next(s["time"] for s in generate_slots(doctor_id, date.fromisoformat(DAY)) if s["available"])

def test_slots_deterministic_and_labelled():
    a = generate_slots("dr-anitha-nair", date.fromisoformat(DAY))
    b = generate_slots("dr-anitha-nair", date.fromisoformat(DAY))
    assert a == b
    r = client.get(f"/api/doctors/dr-anitha-nair/slots?date={DAY}")
    assert r.status_code == 200
    assert r.json()["source"] == "demo_schedule"
    assert len(r.json()["slots"]) == 16

def test_doctors_filter():
    r = client.get("/api/doctors?speciality=Cardiology")
    assert r.status_code == 200
    assert len(r.json()["doctors"]) == 2
    assert all(d["speciality"] == "Cardiology" for d in r.json()["doctors"])

def test_booking_requires_confirmation():
    payload = {"doctor_id": "dr-anitha-nair", "date": DAY, "time": _available_slot("dr-anitha-nair"),
               "patient_name": "Test Patient", "patient_phone": "9999999999", "confirmed": False}
    r = client.post("/api/appointments", json=payload)
    assert r.status_code == 422
    assert r.json()["detail"] == "confirmation_required"

def test_booking_full_loop():
    slot = _available_slot("dr-rahul-menon")
    payload = {"doctor_id": "dr-rahul-menon", "date": DAY, "time": slot,
               "patient_name": "Test Patient", "patient_phone": "9999999999", "confirmed": True}
    r = client.post("/api/appointments", json=payload)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["token"].startswith("CV-")
    assert body["qr_payload"].startswith("CAREVOICE|")
    assert body["waiting_time"]["is_estimate"] is True
    got = client.get(f"/api/appointments/{body['token']}")
    assert got.status_code == 200
    assert got.json()["patient_name"] == "Test Patient"

def test_reschedule_and_cancel():
    slot = _available_slot("dr-sana-khan")
    r = client.post("/api/appointments", json={"doctor_id": "dr-sana-khan", "date": DAY, "time": slot,
                   "patient_name": "P2", "patient_phone": "8888888888", "confirmed": True})
    token = r.json()["token"]
    day2 = (date.today() + timedelta(days=2)).isoformat()
    slot2 = next(s["time"] for s in generate_slots("dr-sana-khan", date.fromisoformat(day2)) if s["available"])
    rr = client.patch(f"/api/appointments/{token}/reschedule", json={"date": day2, "time": slot2})
    assert rr.status_code == 200
    assert rr.json()["date"] == day2
    cc = client.post(f"/api/appointments/{token}/cancel", json={"reason": "Change of plans", "by": "patient"})
    assert cc.status_code == 200
    assert cc.json()["status"] == "cancelled"
