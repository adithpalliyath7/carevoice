"""Medical records: upload, OCR (best-effort, honestly labelled), search,
share tokens, reminders. All data is demo/fictional unless the operator
supplies real files — never present extracted text as verified medical data.
"""
import re
import secrets
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ALLOWED_EXT = {".pdf", ".jpg", ".jpeg", ".png"}
ALLOWED_KINDS = {"prescription", "lab_report", "scan", "discharge", "other"}
MAX_BYTES = 10 * 1024 * 1024
SHARE_TTL_HOURS = 24
ID_RE = re.compile(r"^[A-Za-z0-9_-]{8,64}$")

RECORDS: dict[str, dict] = {}
SHARE_TOKENS: dict[str, dict] = {}   # token -> {record_id, expires_at}
REMINDERS: dict[str, dict] = {}


def _ocr_available() -> tuple[bool, str]:
    """pytesseract needs the tesseract binary; report its real status."""
    try:
        import pytesseract  # noqa
        from shutil import which
        return (which("tesseract") is not None, "tesseract" if which("tesseract") else "missing-binary")
    except ImportError:
        return False, "pytesseract-not-installed"


def extract_text(data: bytes, filename: str) -> tuple[str, str, float | None]:
    """Returns (text, ocr_status, confidence). Status: ok / partial / unavailable.
    Never claims success when extraction failed."""
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        try:
            from pypdf import PdfReader
            import io
            reader = PdfReader(io.BytesIO(data))
            text = "\n".join((p.extract_text() or "") for p in reader.pages)
            if text.strip():
                return text.strip(), "ok", None
            return "", "partial", None  # scanned PDF, no embedded text
        except Exception:
            return "", "unavailable", None
    if ext in (".jpg", ".jpeg", ".png"):
        ok, why = _ocr_available()
        if not ok:
            return "", "unavailable", None
        try:
            import pytesseract
            from PIL import Image
            import io
            img = Image.open(io.BytesIO(data))
            data_out = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
            words = [w for w in data_out.get("text", []) if w.strip()]
            confs = [float(c) for c in data_out.get("conf", []) if str(c).strip("-").isdigit()]
            conf = round(sum(confs) / len(confs) / 100, 2) if confs else None
            text = " ".join(words)
            return text, ("ok" if text.strip() else "partial"), conf
        except Exception:
            return "", "unavailable", None
    return "", "unavailable", None


DATE_RE = re.compile(r"\b(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})\b")
DOSAGE_RE = re.compile(r"^.*\b\d+\s*(?:-\s*\d+\s*-\s*\d+|\d*\s*mg|\d*\s*ml)\b.*$|^.*\b(tablet|capsule|syrup|injection|drops)\b.*$", re.I | re.M)
MED_LINE_RE = re.compile(r"^\s*(?:\d+[.)]\s*)?([A-Za-z][A-Za-z ]{2,40}?)\s+(\d+\s*(?:mg|ml|g)\b[^,\n]{0,30}|\d\s*-\s*\d\s*-\s*\d[^,\n]{0,30})", re.I | re.M)


def extract_fields(text: str, form: dict) -> dict:
    """Regex-only extraction from OCR text. Everything is labelled extracted,
    not verified."""
    dates = [d.group(0) for d in DATE_RE.finditer(text or "")][:3]
    meds = []
    for m in MED_LINE_RE.finditer(text or ""):
        meds.append({"name": m.group(1).strip(), "dosage": m.group(2).strip()})
        if len(meds) >= 10:
            break
    lab_values = []
    for line in (text or "").splitlines():
        if re.search(r"(?i)(haemoglobin|hemoglobin|sugar|cholesterol|creatinine|wbc|rbc|platelet)", line) \
                and re.search(r"\d+(\.\d+)?", line):
            lab_values.append(line.strip()[:120])
            if len(lab_values) >= 10:
                break
    return {"dates_found": dates,
            "medicines": meds,
            "lab_values": lab_values,
            "doctor_name": form.get("doctor_name"),
            "patient_name": form.get("patient_name")}


def create_record(meta: dict, filename: str, size: int, content_type: str,
                  storage_ref: str, extracted_text: str, ocr_status: str,
                  confidence: float | None) -> dict:
    rid = uuid.uuid4().hex[:16]
    rec_date = meta.get("date") or date.today().isoformat()
    rec = {"id": rid, "filename": Path(filename).name, "kind": meta.get("kind", "other"),
           "doctor_name": meta.get("doctor_name"), "patient_name": meta.get("patient_name"),
           "patient_phone": meta.get("patient_phone"), "date": rec_date,
           "notes": meta.get("notes"), "size_bytes": size, "content_type": content_type,
           "storage_ref": storage_ref, "extracted_text": extracted_text,
           "ocr_status": ocr_status, "ocr_confidence": confidence,
           "fields": extract_fields(extracted_text, meta),
           "doctor_notes": None, "created_at": datetime.now(timezone.utc).isoformat()}
    RECORDS[rid] = rec
    return rec


def public_record(rec: dict) -> dict:
    return {k: v for k, v in rec.items() if k not in ("storage_ref", "patient_phone")}


def list_records(kind=None, doctor=None, q=None, sort="date"):
    out = list(RECORDS.values())
    if kind:
        out = [r for r in out if r["kind"] == kind]
    if doctor:
        out = [r for r in out if (r.get("doctor_name") or "").lower().find(doctor.lower()) >= 0]
    if q:
        ql = q.lower()
        out = [r for r in out if ql in (r.get("extracted_text") or "").lower()
               or ql in (r.get("doctor_name") or "").lower()
               or ql in (r.get("kind") or "").lower()
               or ql in (r.get("patient_name") or "").lower()]
    out.sort(key=lambda r: r.get("date", ""), reverse=(sort != "date_asc"))
    return out


def search_voice(transcript: str, limit: int = 10) -> list[dict]:
    """Parse date words / doctor / medicine names out of a transcript and rank."""
    t = (transcript or "").lower()
    scored = []
    for rec in RECORDS.values():
        score = 0
        hay = " ".join([rec.get("doctor_name") or "", rec.get("kind") or "",
                        rec.get("extracted_text") or "",
                        rec.get("patient_name") or ""]).lower()
        for word in re.findall(r"[a-z]{3,}", t):
            if word in hay:
                score += 1
        if "last month" in t:
            try:
                rd = date.fromisoformat(rec["date"])
                if (date.today() - rd).days <= 45:
                    score += 2
            except ValueError:
                pass
        if score:
            scored.append((score, rec))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [public_record(r) for _, r in scored[:limit]]


def create_share_token(record_id: str, ttl_hours: int = SHARE_TTL_HOURS) -> dict:
    token = secrets.token_urlsafe(24)
    expires = datetime.now(timezone.utc) + timedelta(hours=ttl_hours)
    SHARE_TOKENS[token] = {"record_id": record_id, "expires_at": expires}
    return {"token": token, "url": f"/api/records/shared/{token}",
            "expires_at": expires.isoformat(), "expires_in_hours": ttl_hours}


def resolve_share_token(token: str):
    entry = SHARE_TOKENS.get(token)
    if not entry:
        return None, "not_found"
    if datetime.now(timezone.utc) > entry["expires_at"]:
        del SHARE_TOKENS[token]
        return None, "expired"
    return entry["record_id"], "ok"


def create_reminder(payload: dict) -> dict:
    rid = uuid.uuid4().hex[:12]
    rem = {"id": rid, "record_id": payload.get("record_id"),
           "appointment_token": payload.get("appointment_token"),
           "type": payload.get("type", "prescription_refill"),
           "due_date": payload.get("due_date"), "note": payload.get("note"),
           "language": payload.get("language", "en"),
           "created_at": datetime.now(timezone.utc).isoformat()}
    try:
        due = date.fromisoformat(payload["due_date"])
        rem["due_today"] = due == date.today()
        rem["days_until_due"] = (due - date.today()).days
    except (ValueError, TypeError):
        rem["due_today"] = False
        rem["days_until_due"] = None
    REMINDERS[rid] = rem
    return rem


def list_reminders(due_before: str | None = None):
    out = sorted(REMINDERS.values(), key=lambda r: r.get("due_date", ""))
    if due_before:
        out = [r for r in out if r.get("due_date", "") <= due_before]
    return out
