from datetime import date
from fastapi import APIRouter, HTTPException
from ..schemas import AppointmentCreate, AppointmentReschedule
from .. import bookings
from ..ops import check_in, cancel_booking, DELAYS
from ..slots import waiting_time_minutes

router = APIRouter(prefix="/api/appointments", tags=["appointments"])


@router.post("")
def create(payload: AppointmentCreate):
    status, body = bookings.create_booking(payload.model_dump())
    if status >= 400:
        raise HTTPException(status, body.get("error", "error")
                            if isinstance(body, dict) else "error")
    return body


@router.get("")
def by_phone(patient_phone: str):
    return {"appointments": bookings.list_by_phone(patient_phone)}


@router.get("/{token}")
def get_one(token: str):
    appt = bookings.get_booking(token)
    if not appt:
        raise HTTPException(404, "appointment_not_found")
    delay = DELAYS.get(appt["doctor_id"])
    out = dict(appt)
    if delay:
        out["delay_minutes"] = delay["delay_minutes"]
        out["delay_announcement"] = delay["message"]
    return out


@router.get("/{token}/queue-position")
def queue_position(token: str):
    from ..ops import get_queue
    appt = bookings.get_booking(token)
    if not appt:
        raise HTTPException(404, "appointment_not_found")
    q = get_queue(appt["doctor_id"], appt["date"])
    entry = next((e for e in q if e["token"] == token), None)
    wait = waiting_time_minutes(appt["doctor_id"], date.fromisoformat(appt["date"]), appt["time"])
    return {"token": token, "status": appt["status"],
            "queue_position": entry["position"] if entry else None,
            "queue_status": entry["status"] if entry else "not_checked_in",
            "estimated_wait_minutes": wait["estimated_wait_minutes"],
            "is_estimate": True}


@router.post("/{token}/check-in")
def self_check_in(token: str):
    status, body = check_in(token)
    if status >= 400:
        raise HTTPException(status, body.get("error", "error"))
    return body


@router.patch("/{token}/reschedule")
def resched(token: str, payload: AppointmentReschedule):
    status, body = bookings.reschedule(token, payload.date, payload.time)
    if status >= 400:
        raise HTTPException(status, body.get("error", "error"))
    return body


@router.delete("/{token}")
def cancel(token: str, reason: str = "", by: str = "patient"):
    status, body = cancel_booking(token, reason or "Cancelled by patient", by)
    if status >= 400:
        raise HTTPException(status, body.get("error", "error"))
    return body


@router.post("/{token}/cancel")
def cancel_with_reason(token: str, payload: dict):
    status, body = cancel_booking(token, payload.get("reason", ""), payload.get("by", "patient"))
    if status >= 400:
        raise HTTPException(status, body.get("error", "error"))
    return body
