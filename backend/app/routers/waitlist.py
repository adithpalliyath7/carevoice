from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from .. import waitlist as wl

router = APIRouter(prefix="/api/waitlist", tags=["waitlist"])


@router.post("")
def join(payload: dict):
    if not payload.get("doctor_id") or not payload.get("date") or not payload.get("patient_name"):
        raise HTTPException(400, "doctor_id, date and patient_name are required")
    return wl.join(payload)


@router.get("/{entry_id}")
def get_one(entry_id: str):
    entry = wl.get_entry(entry_id)
    if not entry:
        raise HTTPException(404, "waitlist_entry_not_found")
    return entry


@router.post("/{entry_id}/accept")
def accept(entry_id: str, payload: dict):
    status, body = wl.accept(entry_id, bool(payload.get("confirmed")))
    if status >= 400:
        raise HTTPException(status, body.get("error", "error"))
    return JSONResponse(status_code=status, content=body)


@router.post("/{entry_id}/decline")
def decline(entry_id: str):
    status, body = wl.decline(entry_id)
    if status >= 400:
        raise HTTPException(status, body.get("error", "error"))
    return body
