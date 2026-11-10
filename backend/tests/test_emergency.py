from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_emergency_transcript_bypasses_booking():
    for text in ["I'm having a medical emergency. Help me find the nearest hospital.",
                 "mujhe madad chahiye, emergency hai",
                 "enikku sahayam venam, emergency",
                 "chest pain, I can't breathe"]:
        r = client.post("/api/voice/converse",
                        json={"transcript": text, "language": "en", "session": {}})
        body = r.json()
        assert body.get("emergency") is True, text
        assert body.get("action") == "show_emergency_screen"
        assert body.get("needs_clarification") is False
        assert body.get("intent") == "emergency"


def test_emergency_response_has_no_diagnosis_or_questions():
    r = client.post("/api/voice/converse",
                    json={"transcript": "emergency, help me", "language": "en", "session": {}})
    body = r.json()
    blob = (body.get("speak_text", "") + body.get("reply_text", "")).lower()
    assert "diagnos" not in blob
    assert "symptom" not in blob
    assert "?" not in blob  # no questions — immediate action only
    assert "108" in blob or "112" in blob


def test_emergency_post_contacts_payload():
    r = client.post("/api/support/emergency", json={"language": "en", "consent_given": False})
    body = r.json()
    assert body["ambulance"] == "108"
    assert body["national_emergency"] == "112"
    assert body["nearby_departments"] == []
    assert "demo" in body["hospital"]["note"].lower()


def test_nearby_empty_without_location_consent():
    r = client.get("/api/support/emergency-departments")
    body = r.json()
    assert body["departments"] == []
    assert "location" in body["note"].lower()
    # With location: only the seeded demo hospital, with straight-line distance
    r2 = client.get("/api/support/emergency-departments", params={"lat": 9.93, "lng": 76.26})
    deps = r2.json()["departments"]
    assert len(deps) == 1
    assert deps[0]["is_demo"] is True
    assert "distance_km" in deps[0]
    assert "responder" not in str(deps).lower()
    assert "eta" not in str(deps).lower()


def test_sos_flow_needs_no_confirmation():
    # The emergency endpoint answers immediately; no confirm step exists.
    r = client.post("/api/support/emergency",
                    json={"language": "hi", "consent_given": True,
                          "latitude": 9.93, "longitude": 76.26})
    assert r.status_code == 200
    assert r.json()["nearby_departments"]
    assert "confirmation" not in str(r.json()).lower()
    # Hindi speak text is returned for Timbre
    assert r.json()["speak_text"]
