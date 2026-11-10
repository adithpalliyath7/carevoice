from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_root():
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["service"] == "CareVoice"

def test_health_shape():
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert isinstance(body["gnani_configured"], bool)
    assert "GNANI_API_KEY" not in str(body)  # never leak the key
    assert body["demo_mode"] is True

def test_transcribe_without_key_is_503():
    # No key in this environment -> honest 503, never a fake transcript.
    r = client.post("/api/voice/transcribe", files={"audio_file": ("a.webm", b"\x00\x01", "audio/webm")},
                    data={"language": "en-IN"})
    assert r.status_code == 503
    assert r.json()["error"] == "gnani_not_configured"

def test_speak_without_key_is_503():
    r = client.post("/api/voice/speak", json={"text": "Hello", "language": "en"})
    assert r.status_code == 503
    assert r.json()["error"] == "gnani_not_configured"
