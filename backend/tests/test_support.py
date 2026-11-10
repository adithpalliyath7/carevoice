from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_glossary_hit():
    r = client.get("/api/support/glossary", params={"term": "bp", "language": "en"})
    assert r.status_code == 200
    assert "bp" in r.json()["results"]
    assert "blood pressure" in r.json()["results"]["bp"].lower()

def test_ask_covered_question():
    r = client.post("/api/support/ask", json={"question": "How do I book an appointment?", "language": "en"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "answered"
    assert body["answer"]
    assert "does not diagnose" in body["safety_notice"]

def test_unknown_question_never_invents_advice():
    r = client.post("/api/support/ask", json={"question": "What dose of metformin should I take for my diabetes?", "language": "en"})
    body = r.json()
    assert body["status"] == "not_covered"
    assert body["answer"] is None
    assert body["suggested_action"] == "ask_doctor"
    assert body["questions_to_ask"]

def test_post_visit_no_notes_safe_fallback():
    r = client.get("/api/support/post-visit", params={"appointment_token": "CV-20990101-XXXX"})
    body = r.json()
    assert body["status"] == "none_on_file"
    assert body["instructions"] is None
    assert "discharge" in body["note"].lower() or "prescription" in body["note"].lower()

def test_emergency_payload_has_real_numbers():
    r = client.get("/api/support/emergency")
    body = r.json()
    assert body["ambulance"] == "108"
    assert body["national_emergency"] == "112"
    assert body["is_demo"] is True

def test_escalate_returns_reference_and_emergency_routing():
    r = client.post("/api/support/escalate", json={"patient_name": "P", "concern": "I have chest pain", "severity": "routine"})
    body = r.json()
    assert body["reference_id"].startswith("ESC-")
    assert body["severity"] == "emergency"  # keyword routing overrides routine
    assert "108" in body["next_step"]

def test_prepare_visit_checklist():
    r = client.post("/api/support/prepare-visit", json={"speciality": "cardiology"})
    body = r.json()
    assert len(body["prep_checklist"]) >= 3
    assert body["questions_to_ask"]
    assert "not medical advice" in body["label"]
