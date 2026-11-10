"""Medical records router: upload / list / download / share / voice search / reminders."""
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, Header, HTTPException, Query
from fastapi.responses import FileResponse, Response
from .. import records as rec
from .. import storage, gnani
from ..schemas import ReminderCreate
from ..config import MAX_AUDIO_BYTES

router = APIRouter(prefix="/api/records", tags=["records"])


def _validate_id(rid: str):
    if not rec.ID_RE.match(rid or ""):
        raise HTTPException(400, "invalid_record_id")
    return rid


@router.post("/upload")
async def upload(file: UploadFile = File(...),
                 patient_name: str | None = Form(None),
                 patient_phone: str | None = Form(None),
                 doctor_name: str | None = Form(None),
                 date: str | None = Form(None),
                 kind: str = Form("other"),
                 notes: str | None = Form(None)):
    if kind not in rec.ALLOWED_KINDS:
        raise HTTPException(400, "invalid_kind")
    data = await file.read()
    if len(data) > rec.MAX_BYTES:
        raise HTTPException(413, "file_too_large")
    ext = Path(file.filename or "").suffix.lower()
    if ext not in rec.ALLOWED_EXT:
        raise HTTPException(400, "unsupported_file_type")
    meta = {"patient_name": patient_name, "patient_phone": patient_phone,
            "doctor_name": doctor_name, "date": date, "kind": kind, "notes": notes}
    text, ocr_status, conf = rec.extract_text(data, file.filename or "file")
    # Create first (needs id), then store the file under it.
    record = rec.create_record(meta, file.filename or "file", len(data),
                               file.content_type or "application/octet-stream",
                               "", text, ocr_status, conf)
    ref = storage.save_file(record["id"], file.filename or "file", data)
    record["storage_ref"] = ref
    return {**rec.public_record(record),
            "download_url": f"/api/records/{record['id']}/download",
            "ocr_note": "Extracted text is unverified — always check the original file."}


@router.get("")
def list_all(sort: str = "date", doctor: str | None = None,
             kind: str | None = None, q: str | None = None):
    return {"records": [rec.public_record(r) for r in rec.list_records(kind, doctor, q, sort)],
            "count": len(rec.RECORDS)}


@router.get("/search/voice")
def voice_search_get(transcript: str | None = None, q: str | None = None):
    query = transcript or q or ""
    return {"query": query, "records": rec.search_voice(query)}


@router.post("/search/voice")
async def voice_search_post(audio_file: UploadFile = File(...),
                            language: str = Form("en-IN")):
    data = await audio_file.read()
    try:
        result = await gnani.transcribe(data, audio_file.filename or "audio.webm", language)
    except gnani.GnaniError as e:
        raise HTTPException(e.status, e.detail or e.code)
    return {"transcript": result["transcript"],
            "records": rec.search_voice(result["transcript"])}


# ---- Reminders ----
@router.post("/reminders")
def create_reminder(payload: ReminderCreate):
    if payload.record_id and payload.record_id not in rec.RECORDS:
        raise HTTPException(404, "record_not_found")
    rem = rec.create_reminder(payload.model_dump())
    return {**rem, "note": "MVP reminder: no SMS/email is sent. Check the list in the app."}


@router.get("/reminders")
def list_reminders(due_before: str | None = None):
    return {"reminders": rec.list_reminders(due_before)}


@router.post("/reminders/{reminder_id}/speak")
async def speak_reminder(reminder_id: str):
    rem = rec.REMINDERS.get(reminder_id)
    if not rem:
        raise HTTPException(404, "reminder_not_found")
    text = (f"Reminder: {rem['type'].replace('_', ' ')} is due on {rem['due_date']}. "
            f"{rem.get('note') or ''}")
    try:
        audio, ctype = await gnani.synthesize(text, rem.get("language", "en"))
    except gnani.GnaniError as e:
        raise HTTPException(e.status, e.detail or e.code)
    return Response(content=audio, media_type=ctype)


@router.get("/{record_id}")
def get_one(record_id: str):
    _validate_id(record_id)
    r = rec.RECORDS.get(record_id)
    if not r:
        raise HTTPException(404, "record_not_found")
    return rec.public_record(r)


def _authorize(r: dict, x_patient_phone: str | None, token_ok: bool):
    if token_ok:
        return
    if x_patient_phone and r.get("patient_phone") and x_patient_phone == r["patient_phone"]:
        return
    if not r.get("patient_phone"):
        return  # demo record with no phone on file: allow in MVP demo mode
    raise HTTPException(403, "patient_phone_required")


@router.get("/{record_id}/download")
def download(record_id: str, x_patient_phone: str | None = Header(None)):
    _validate_id(record_id)
    r = rec.RECORDS.get(record_id)
    if not r:
        raise HTTPException(404, "record_not_found")
    _authorize(r, x_patient_phone, False)
    path = Path(r["storage_ref"])
    if not path.exists():
        raise HTTPException(404, "file_missing")
    return FileResponse(path, media_type=r["content_type"], filename=r["filename"])


@router.post("/{record_id}/share")
def share(record_id: str):
    _validate_id(record_id)
    if record_id not in rec.RECORDS:
        raise HTTPException(404, "record_not_found")
    return rec.create_share_token(record_id)


@router.get("/shared/{token}")
def shared_download(token: str):
    record_id, status = rec.resolve_share_token(token)
    if status == "expired":
        raise HTTPException(410, "share_link_expired")
    if not record_id or record_id not in rec.RECORDS:
        raise HTTPException(404, "share_link_not_found")
    r = rec.RECORDS[record_id]
    path = Path(r["storage_ref"])
    if not path.exists():
        raise HTTPException(404, "file_missing")
    return FileResponse(path, media_type=r["content_type"], filename=r["filename"])


