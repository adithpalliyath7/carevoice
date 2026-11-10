"""In-memory appointment store (MVP). Optional Supabase insert if configured —
never required for the demo to work. Bookings require confirmed=True."""
import random
import string
from datetime import date
from .data import get_doctor, generate_slots
from .slots import waiting_time_minutes

STORE: dict[str, dict] = {}


def _token() -> str:
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"CV-{date.today().strftime('%Y%m%d')}-{suffix}"


def create_booking(payload: dict) -> dict:
    """Returns (status, body). 422 confirmation_required unless confirmed=True."""
    if not payload.get("confirmed"):
        doctor = get_doctor(payload.get("doctor_id", ""))
        summary = {
            "doctor": doctor["name"] if doctor else payload.get("doctor_id"),
            "speciality": doctor["speciality"] if doctor else None,
            "date": payload.get("date"), "time": payload.get("time"),
            "patient_name": payload.get("patient_name"),
            "for_family_member": payload.get("for_family_member"),
            "fee_inr": doctor["fee_inr"] if doctor else None,
        }
        return 422, {"error": "confirmation_required",
                     "message": "Please review the summary and confirm explicitly before booking.",
                     "summary": summary}
    doctor = get_doctor(payload.get("doctor_id", ""))
    if not doctor:
        return 404, {"error": "doctor_not_found"}
    try:
        day = date.fromisoformat(payload["date"])
    except (ValueError, KeyError):
        return 400, {"error": "invalid_date", "message": "date must be YYYY-MM-DD"}
    slot = next((s for s in generate_slots(doctor["id"], day)
                 if s["time"] == payload.get("time")), None)
    if not slot:
        return 400, {"error": "invalid_time", "message": "No such slot in the demo schedule."}
    # A cancelled booking frees its slot; staff-blocked slots stay blocked.
    freed_by_cancellation = any(
        a["doctor_id"] == doctor["id"] and a["date"] == payload["date"]
        and a["time"] == payload.get("time") and a.get("status") == "cancelled"
        for a in STORE.values())
    try:
        from .ops import AVAILABILITY
        blocked = (payload["date"] in AVAILABILITY.get(doctor["id"], {}).get("blocked_dates", {})) \
            or ((payload["date"], payload.get("time")) in
                AVAILABILITY.get(doctor["id"], {}).get("blocked_slots", {}))
    except Exception:
        blocked = False
    if blocked:
        return 409, {"error": "slot_unavailable",
                     "message": "That slot is blocked by the hospital. Please choose another time."}
    if not slot["available"] and not freed_by_cancellation:
        return 409, {"error": "slot_unavailable",
                     "message": "That demo slot is already taken. Please choose another time."}
    wait = waiting_time_minutes(doctor["id"], day, payload["time"])
    token = _token()
    appt = {"token": token, "doctor_id": doctor["id"], "doctor_name": doctor["name"],
            "speciality": doctor["speciality"], "date": payload["date"],
            "time": payload["time"], "patient_name": payload.get("patient_name"),
            "patient_phone": payload.get("patient_phone"),
            "patient_age": payload.get("patient_age"),
            "for_family_member": payload.get("for_family_member"),
            "fee_inr": doctor["fee_inr"], "status": "confirmed",
            "waiting_time": wait, "source": "demo_schedule",
            "qr_payload": f"CAREVOICE|{token}|{doctor['id']}|{payload['date']}|{payload['time']}",
            "doctor_notes": None}
    STORE[token] = appt
    return 201, appt


def get_booking(token: str):
    return STORE.get(token)


def reschedule(token: str, new_date: str, new_time: str):
    appt = STORE.get(token)
    if not appt:
        return 404, {"error": "appointment_not_found"}
    try:
        day = date.fromisoformat(new_date)
    except ValueError:
        return 400, {"error": "invalid_date"}
    slot = next((s for s in generate_slots(appt["doctor_id"], day)
                 if s["time"] == new_time), None)
    if not slot or not slot["available"]:
        return 409, {"error": "slot_unavailable",
                     "message": "That demo slot is not available. Choose another time."}
    appt["date"], appt["time"] = new_date, new_time
    appt["waiting_time"] = waiting_time_minutes(appt["doctor_id"], day, new_time)
    appt["qr_payload"] = (f"CAREVOICE|{token}|{appt['doctor_id']}|{new_date}|{new_time}")
    return 200, appt


def cancel(token: str):
    appt = STORE.pop(token, None)
    if not appt:
        return 404, {"error": "appointment_not_found"}
    appt["status"] = "cancelled"
    return 200, appt


def list_by_phone(phone: str):
    return [a for a in STORE.values() if a.get("patient_phone") == phone]
