"""Hospital operations: role-gated staff flows, availability, queue, check-in,
cancellations, delays, analytics.

DEMO AUTH ONLY: demo users receptionist@demo / admin@demo, password "demo1234",
role carried on X-Demo-Role + a demo token from POST /api/ops/login. Real
auth (JWT / Supabase Auth) MUST replace this before production.
"""
import secrets
from collections import Counter
from datetime import date
from .data import DOCTORS, get_doctor, generate_slots
from .bookings import STORE, create_booking
from .slots import waiting_time_minutes

DEMO_USERS = {
    "receptionist@demo": {"password": "demo1234", "role": "receptionist", "name": "Demo Receptionist"},
    "admin@demo": {"password": "demo1234", "role": "admin", "name": "Demo Administrator"},
}
TOKENS: dict[str, dict] = {}   # demo token -> {email, role}
# Availability overrides: doctor_id -> {"weekly": {day: {start,end,slot_minutes,active}},
#   "blocked_dates": {date: reason}, "blocked_slots": {(date,time): reason}, "max_per_day": int}
AVAILABILITY: dict[str, dict] = {}
DELAYS: dict[str, dict] = {}   # doctor_id -> {minutes, message, language}
CANCELLATIONS: list[dict] = []
QUEUE: dict[str, list[dict]] = {}  # f"{doctor_id}|{date}" -> [{token, status, position}]
LANGUAGE_COUNTER: Counter = Counter()
ANALYTICS_EVENTS: list[dict] = []


def login(email: str, password: str):
    user = DEMO_USERS.get((email or "").lower())
    if not user or user["password"] != password:
        return None
    token = secrets.token_urlsafe(24)
    TOKENS[token] = {"email": email.lower(), "role": user["role"], "name": user["name"]}
    return {"token": token, "role": user["role"], "name": user["name"]}


def role_from_request(authorization: str | None, demo_role: str | None):
    if authorization and authorization.startswith("Bearer "):
        user = TOKENS.get(authorization[7:])
        if user:
            return user["role"]
    if demo_role in ("receptionist", "admin", "patient"):
        return demo_role
    return None


def track_language(language: str, event: str = "voice"):
    if language:
        LANGUAGE_COUNTER[language] += 1
        ANALYTICS_EVENTS.append({"event": event, "language": language})


def default_weekly():
    return {d: {"start": "09:00", "end": "17:00", "slot_minutes": 30, "active": True}
            for d in ["mon", "tue", "wed", "thu", "fri", "sat"]}


def get_availability(doctor_id: str) -> dict:
    av = AVAILABILITY.setdefault(doctor_id, {"weekly": default_weekly(),
        "blocked_dates": {}, "blocked_slots": {}, "max_per_day": 32})
    return {"doctor_id": doctor_id, "weekly": av["weekly"],
            "blocked_dates": av["blocked_dates"], "max_per_day": av["max_per_day"]}


def update_availability(doctor_id: str, payload: dict) -> dict:
    av = AVAILABILITY.setdefault(doctor_id, {"weekly": default_weekly(),
        "blocked_dates": {}, "blocked_slots": {}, "max_per_day": 32})
    if "weekly" in payload:
        av["weekly"].update(payload["weekly"])
    if "blocked_dates" in payload:
        av["blocked_dates"].update(payload["blocked_dates"])
    if "max_per_day" in payload:
        av["max_per_day"] = payload["max_per_day"]
    return get_availability(doctor_id)


def block_slot(doctor_id: str, day: str, time: str, reason: str):
    av = AVAILABILITY.setdefault(doctor_id, {"weekly": default_weekly(),
        "blocked_dates": {}, "blocked_slots": {}, "max_per_day": 32})
    av["blocked_slots"][(day, time)] = reason or "Blocked by staff"
    return {"doctor_id": doctor_id, "date": day, "time": time, "reason": reason}


def is_slot_available(doctor_id: str, day: str, time: str) -> bool:
    av = AVAILABILITY.get(doctor_id)
    if av:
        if day in av["blocked_dates"]:
            return False
        if (day, time) in av["blocked_slots"]:
            return False
    # Cancelled slots free up: a booking that was cancelled no longer blocks.
    if any(a["doctor_id"] == doctor_id and a["date"] == day and a["time"] == time
           and a.get("status") == "cancelled" for a in STORE.values()):
        return True
    slot = next((s for s in generate_slots(doctor_id, date.fromisoformat(day))
                 if s["time"] == time), None)
    if slot is not None and not slot["available"]:
        # Seeded demo pattern says taken only if a live booking occupies it;
        # without a booking, treat the seeded "taken" as free? No: keep the
        # seeded pattern as the demo schedule, but a cancelled booking frees it.
        return False
    return slot is not None


def effective_slots(doctor_id: str, day):
    slots = generate_slots(doctor_id, day)
    av = AVAILABILITY.get(doctor_id)
    cancelled_keys = {(a["date"], a["time"]) for a in STORE.values()
                      if a["doctor_id"] == doctor_id and a.get("status") == "cancelled"}
    booked_keys = {(a["date"], a["time"]) for a in STORE.values()
                   if a["doctor_id"] == doctor_id and a.get("status") in ("confirmed", "checked-in")}
    out = []
    for s in slots:
        avail = s["available"]
        if av:
            if day.isoformat() in av["blocked_dates"]:
                avail = False
            if (day.isoformat(), s["time"]) in av["blocked_slots"]:
                avail = False
        if (day.isoformat(), s["time"]) in cancelled_keys:
            avail = True
        if (day.isoformat(), s["time"]) in booked_keys:
            avail = False
        out.append({"time": s["time"], "available": avail, "source": "demo_schedule"})
    return out


def create_walk_in(payload: dict):
    status, body = create_booking({**payload, "confirmed": True})
    if status != 201:
        return status, body
    body["source"] = "walk-in"
    body["token"] = body["token"].replace("CV-", "CV-W", 1)
    STORE.pop(body["qr_payload"].split("|")[1] if False else "", None)
    # Re-key under the walk-in token
    old = [k for k, v in STORE.items() if v is body]
    for k in old:
        STORE.pop(k, None)
    body["qr_payload"] = f"CAREVOICE|{body['token']}|{body['doctor_id']}|{body['date']}|{body['time']}"
    STORE[body["token"]] = body
    return 201, body


def queue_key(doctor_id: str, day: str) -> str:
    return f"{doctor_id}|{day}"


def get_queue(doctor_id: str, day: str):
    q = QUEUE.setdefault(queue_key(doctor_id, day), [])
    # Include checked-in bookings not yet in the queue
    seen = {e["token"] for e in q}
    for a in STORE.values():
        if (a["doctor_id"] == doctor_id and a["date"] == day
                and a.get("status") == "checked-in" and a["token"] not in seen):
            q.append({"token": a["token"], "patient_name": a["patient_name"],
                      "status": "waiting", "position": len(q) + 1})
    for i, e in enumerate(q):
        e["position"] = i + 1
    return q


def check_in(token: str):
    appt = STORE.get(token)
    if not appt:
        return 404, {"error": "appointment_not_found"}
    if appt.get("status") == "cancelled":
        return 409, {"error": "appointment_cancelled"}
    appt["status"] = "checked-in"
    q = get_queue(appt["doctor_id"], appt["date"])
    pos = next((e["position"] for e in q if e["token"] == token), len(q))
    wait = waiting_time_minutes(appt["doctor_id"], date.fromisoformat(appt["date"]), appt["time"])
    return 200, {**appt, "queue_position": pos,
                 "estimated_wait_minutes": wait["estimated_wait_minutes"]}


def queue_action(token: str, action: str, order: list[str] | None = None):
    appt = STORE.get(token)
    if not appt:
        return 404, {"error": "appointment_not_found"}
    q = get_queue(appt["doctor_id"], appt["date"])
    entry = next((e for e in q if e["token"] == token), None)
    if action == "call-next":
        waiting = [e for e in q if e["status"] == "waiting"]
        if not waiting:
            return 404, {"error": "queue_empty"}
        nxt = waiting[0]
        nxt["status"] = "in-consultation"
        return 200, {"called": nxt, "queue": q}
    if entry is None:
        return 404, {"error": "not_in_queue", "message": "Patient has not checked in yet."}
    if action == "advance":
        waiting = [e for e in q if e["status"] == "waiting"]
        if waiting:
            waiting[0]["status"] = "in-consultation"
    elif action == "mark-done":
        entry["status"] = "done"
        appt["status"] = "completed"
    elif action == "mark-no-show":
        entry["status"] = "no-show"
        appt["status"] = "no-show"
        CANCELLATIONS.append({"token": token, "date": appt["date"], "reason": "no-show",
                              "cancelled_by": "staff", "doctor_id": appt["doctor_id"]})
    elif action == "reorder" and order:
        by_token = {e["token"]: e for e in q}
        new_q = [by_token[t] for t in order if t in by_token]
        new_q += [e for e in q if e["token"] not in order]
        QUEUE[queue_key(appt["doctor_id"], appt["date"])] = new_q
        q = new_q
    for i, e in enumerate(q):
        e["position"] = i + 1
    return 200, {"queue": q, "entry": entry}


def cancel_booking(token: str, reason: str, by: str):
    appt = STORE.get(token)
    if not appt:
        return 404, {"error": "appointment_not_found"}
    if not reason:
        return 400, {"error": "reason_required",
                     "message": "A cancellation reason is required."}
    appt["status"] = "cancelled"
    CANCELLATIONS.append({"token": token, "date": appt["date"], "reason": reason,
                          "cancelled_by": by, "doctor_id": appt["doctor_id"],
                          "patient_name": appt.get("patient_name")})
    q = QUEUE.get(queue_key(appt["doctor_id"], appt["date"]), [])
    QUEUE[queue_key(appt["doctor_id"], appt["date"])] = [e for e in q if e["token"] != token]
    # Smart waitlist: offer the freed slot to the first waiting patient.
    from . import waitlist as _wl
    offered = _wl.on_slot_cancelled(appt["doctor_id"], appt["date"], appt["time"])
    if offered:
        appt["waitlist_offered_to"] = offered["id"]
    return 200, appt


def set_delay(doctor_id: str, minutes: int, message: str, language: str = "en"):
    DELAYS[doctor_id] = {"doctor_id": doctor_id, "delay_minutes": minutes,
                         "message": message, "language": language}
    return DELAYS[doctor_id]


def daily_analytics(day: str):
    appts = [a for a in STORE.values() if a["date"] == day]
    by_spec, by_doc = Counter(), Counter()
    for a in appts:
        by_spec[a["speciality"]] += 1
        by_doc[a["doctor_name"]] += 1
    waits = [a.get("waiting_time", {}).get("estimated_wait_minutes", 0) for a in appts]
    hours = Counter(a["time"][:2] for a in appts)
    peak = hours.most_common(1)[0][0] + ":00" if hours else None
    return {"date": day, "total": len(appts),
            "booked": sum(1 for a in appts if a.get("status") in ("confirmed", "checked-in", "completed")),
            "walk_in": sum(1 for a in appts if a.get("source") == "walk-in"),
            "online": sum(1 for a in appts if a.get("source") != "walk-in"),
            "checked_in": sum(1 for a in appts if a.get("status") == "checked-in"),
            "completed": sum(1 for a in appts if a.get("status") == "completed"),
            "cancelled": sum(1 for a in appts if a.get("status") == "cancelled"),
            "no_show": sum(1 for a in appts if a.get("status") == "no-show"),
            "by_speciality": dict(by_spec), "by_doctor": dict(by_doc),
            "avg_wait_minutes": round(sum(waits) / len(waits), 1) if waits else 0,
            "peak_hour": peak}
