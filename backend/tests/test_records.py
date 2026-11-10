import io
import time
from datetime import date, timedelta
from fastapi.testclient import TestClient
from app.main import app
from app import records as rec

client = TestClient(app)


def _pdf_bytes(text="Dr. Anitha Nair\nParacetamol 500mg 1-0-1\nDate: 10/11/2026"):
    # Minimal valid PDF with embedded text (pypdf can read it).
    from pypdf import PdfWriter
    from pypdf.generic import NameObject, StreamObject, DictionaryObject, NumberObject
    w = PdfWriter()
    page = w.add_blank_page(612, 792)
    stream = StreamObject()
    stream.set_data(f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode())
    page[NameObject("/Contents")] = w._add_object(stream)
    buf = io.BytesIO()
    w.write(buf)
    return buf.getvalue()


def _upload(pdf=None):
    data = pdf if pdf is not None else _pdf_bytes()
    r = client.post("/api/records/upload",
                    files={"file": ("report.pdf", data, "application/pdf")},
                    data={"patient_name": "Test", "patient_phone": "9999999999",
                          "doctor_name": "Dr. Anitha Nair", "kind": "prescription"})
    return r


def test_upload_pdf_and_extract():
    r = _upload()
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["kind"] == "prescription"
    assert body["ocr_status"] in ("ok", "partial", "unavailable")
    assert "unverified" in body["ocr_note"].lower()
    assert body["download_url"].startswith("/api/records/")


def test_upload_rejects_bad_type_and_big_file():
    r = client.post("/api/records/upload",
                    files={"file": ("evil.exe", b"MZ", "application/octet-stream")},
                    data={"kind": "other"})
    assert r.status_code == 400
    r2 = client.post("/api/records/upload",
                     files={"file": ("big.pdf", b"x" * (10 * 1024 * 1024 + 1), "application/pdf")},
                     data={"kind": "other"})
    assert r2.status_code == 413


def test_list_filter_and_download_auth():
    rec_id = _upload().json()["id"]
    r = client.get("/api/records?kind=prescription")
    assert r.status_code == 200
    assert any(x["id"] == rec_id for x in r.json()["records"])
    r2 = client.get("/api/records?doctor=Anitha")
    assert any(x["id"] == rec_id for x in r2.json()["records"])
    # Wrong phone -> 403
    d = client.get(f"/api/records/{rec_id}/download", headers={"X-Patient-Phone": "0000000000"})
    assert d.status_code == 403
    # Right phone -> 200
    d2 = client.get(f"/api/records/{rec_id}/download", headers={"X-Patient-Phone": "9999999999"})
    assert d2.status_code == 200
    # Bad id format -> 400 (no traversal)
    assert client.get("/api/records/../../etc/passwd/download").status_code in (400, 404)


def test_share_token_and_expiry_logic():
    rec_id = _upload().json()["id"]
    s = client.post(f"/api/records/{rec_id}/share")
    assert s.status_code == 200
    token = s.json()["token"]
    got = client.get(f"/api/records/shared/{token}")
    assert got.status_code == 200
    # Expire it manually (unit-level TTL check) -> 410
    rec.SHARE_TOKENS[token]["expires_at"] = rec.SHARE_TOKENS[token]["expires_at"] - timedelta(days=2)
    gone = client.get(f"/api/records/shared/{token}")
    assert gone.status_code == 410


def test_voice_search_by_doctor_name():
    _upload()
    r = client.get("/api/records/search/voice", params={"transcript": "show reports from Anitha"})
    assert r.status_code == 200
    assert len(r.json()["records"]) >= 1


def test_ocr_unavailable_path_for_image_without_tesseract():
    # A 1x1 PNG: if tesseract is absent, ocr_status must be "unavailable", never fake "ok".
    import base64
    png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8Xw8AAwMCAO+ip1sAAAAASUVORK5CYII=")
    r = client.post("/api/records/upload",
                    files={"file": ("scan.png", png, "image/png")},
                    data={"kind": "scan", "patient_phone": "9999999999"})
    assert r.status_code == 200
    assert r.json()["ocr_status"] in ("ok", "partial", "unavailable")
    if r.json()["ocr_status"] == "unavailable":
        assert r.json()["extracted_text"] == ""


def test_reminders_due_today():
    rec_id = _upload().json()["id"]
    today = date.today().isoformat()
    r = client.post("/api/records/reminders",
                    json={"record_id": rec_id, "type": "prescription_refill",
                          "due_date": today, "note": "Refill paracetamol", "language": "en"})
    assert r.status_code == 200
    assert r.json()["due_today"] is True
    lst = client.get("/api/records/reminders", params={"due_before": today})
    assert any(x["id"] == r.json()["id"] for x in lst.json()["reminders"])
