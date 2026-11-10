"""Smart cancellation waitlist.

When a slot is cancelled, the first waiting patient for that doctor/date is
offered the freed slot (30-minute offer window). Offers expire and roll to the
next person. Accepting requires explicit confirmation, like any booking.
"""
import uuid
from datetime import datetime, timedelta, timezone

OFFER_TTL_MINUTES = 30
WAITLIST: list[dict] = []


def join(payload: dict) -> dict:
    entry = {"id": "WL-" + uuid.uuid4().hex[:8].upper(),
             "doctor_id": payload.get("doctor_id"), "date": payload.get("date"),
             "preferred_time": payload.get("preferred_time"),
             "patient_name": payload.get("patient_name"), "phone": payload.get("phone"),
             "language": payload.get("language", "en"),
             "status": "waiting", "offer": None,
             "created_at": datetime.now(timezone.utc).isoformat()}
    WAITLIST.append(entry)
    return entry


def _expire_stale(now=None):
    """Expired offers roll forward: mark expired and offer the slot to the next
    waiting patient for the same doctor/date/time."""
    now = now or datetime.now(timezone.utc)
    for entry in list(WAITLIST):
        offer = entry.get("offer")
        if entry["status"] == "offered" and offer:
            if datetime.fromisoformat(offer["expires_at"]) <= now:
                entry["status"] = "expired"
                entry["offer"] = None
                _offer_next(entry["doctor_id"], entry["date"], offer["time"])


def _offer_next(doctor_id: str, day: str, time: str):
    for entry in WAITLIST:
        if (entry["doctor_id"] == doctor_id and entry["date"] == day
                and entry["status"] == "waiting"
                and (not entry.get("preferred_time") or entry["preferred_time"] == time)):
            expires = datetime.now(timezone.utc) + timedelta(minutes=OFFER_TTL_MINUTES)
            entry["status"] = "offered"
            entry["offer"] = {"time": time, "expires_at": expires.isoformat(),
                              "expires_in_minutes": OFFER_TTL_MINUTES}
            return entry
    return None


def on_slot_cancelled(doctor_id: str, day: str, time: str):
    """Called by ops.cancel_booking. Returns the entry that was offered, if any."""
    _expire_stale()
    return _offer_next(doctor_id, day, time)


def get_entry(entry_id: str):
    _expire_stale()
    return next((e for e in WAITLIST if e["id"] == entry_id), None)


def accept(entry_id: str, confirmed: bool):
    """Books the offered slot. confirmed=False -> 422 confirmation_required."""
    entry = get_entry(entry_id)
    if not entry:
        return 404, {"error": "waitlist_entry_not_found"}
    if entry["status"] != "offered" or not entry.get("offer"):
        return 409, {"error": "no_active_offer",
                     "message": "No active offer for this waitlist entry."}
    if not confirmed:
        return 422, {"error": "confirmation_required",
                     "message": "Review the offered slot and confirm explicitly to book it.",
                     "summary": {"doctor_id": entry["doctor_id"], "date": entry["date"],
                                 "time": entry["offer"]["time"],
                                 "patient_name": entry["patient_name"]}}
    from .bookings import create_booking
    status, body = create_booking({"doctor_id": entry["doctor_id"], "date": entry["date"],
                                   "time": entry["offer"]["time"],
                                   "patient_name": entry["patient_name"],
                                   "patient_phone": entry["phone"],
                                   "language": entry["language"], "confirmed": True})
    if status != 201:
        return status, body
    entry["status"] = "accepted"
    entry["offer"] = None
    entry["appointment_token"] = body["token"]
    return 201, {**body, "waitlist_id": entry["id"]}


def decline(entry_id: str):
    entry = get_entry(entry_id)
    if not entry:
        return 404, {"error": "waitlist_entry_not_found"}
    if entry["status"] == "offered" and entry.get("offer"):
        offer_time = entry["offer"]["time"]
        entry["status"] = "declined"
        entry["offer"] = None
        _offer_next(entry["doctor_id"], entry["date"], offer_time)
        return 200, entry
    entry["status"] = "declined"
    return 200, entry


def list_for_staff(doctor_id=None, day=None):
    _expire_stale()
    out = list(WAITLIST)
    if doctor_id:
        out = [e for e in out if e["doctor_id"] == doctor_id]
    if day:
        out = [e for e in out if e["date"] == day]
    return out
