"""Staff operations router. Role-gated: receptionist or admin.
Demo auth only — see app/ops.py header. Patients get 403."""
from fastapi import APIRouter, Header, HTTPException, Query
from .. import ops
from ..bookings import STORE

router = APIRouter(prefix="/api/ops", tags=["ops"])


def _require_staff(authorization: str | None = Header(None),
                   x_demo_role: str | None = Header(None)):
    role = ops.role_from_request(authorization, x_demo_role)
    if role not in ("receptionist", "admin"):
        raise HTTPException(403, "staff_only")
    return role


def _require_admin(authorization: str | None = Header(None),
                   x_demo_role: str | None = Header(None)):
    role = ops.role_from_request(authorization, x_demo_role)
    if role != "admin":
        raise HTTPException(403, "admin_only")
    return role


@router.post("/login")
def login(payload: dict):
    result = ops.login(payload.get("email", ""), payload.get("password", ""))
    if not result:
        raise HTTPException(401, "invalid_credentials")
    return {**result, "warning": "DEMO ONLY — replace with JWT / Supabase Auth before production."}


def _dep_staff(authorization: str | None = Header(None), x_demo_role: str | None = Header(None)):
    return _require_staff(authorization, x_demo_role)


@router.get("/appointments")
def list_appts(role: str = None, date: str | None = None, doctor_id: str | None = None,
               status: str | None = None, source: str | None = None,
               authorization: str | None = Header(None), x_demo_role: str | None = Header(None)):
    _require_staff(authorization, x_demo_role)
    out = list(STORE.values())
    if date:
        out = [a for a in out if a["date"] == date]
    if doctor_id:
        out = [a for a in out if a["doctor_id"] == doctor_id]
    if status:
        out = [a for a in out if a["status"] == status]
    if source:
        out = [a for a in out if a.get("source") == source]
    return {"appointments": out, "count": len(out)}


@router.post("/walk-in")
def walk_in(payload: dict, authorization: str | None = Header(None),
            x_demo_role: str | None = Header(None)):
    _require_staff(authorization, x_demo_role)
    status, body = ops.create_walk_in(payload)
    if status >= 400:
        raise HTTPException(status, body.get("error", "error"))
    return body


@router.get("/doctors/{doctor_id}/availability")
def get_avail(doctor_id: str, authorization: str | None = Header(None),
              x_demo_role: str | None = Header(None)):
    _require_staff(authorization, x_demo_role)
    return ops.get_availability(doctor_id)


@router.put("/doctors/{doctor_id}/availability")
def put_avail(doctor_id: str, payload: dict, authorization: str | None = Header(None),
              x_demo_role: str | None = Header(None)):
    _require_admin(authorization, x_demo_role)
    return ops.update_availability(doctor_id, payload)


@router.post("/doctors/{doctor_id}/block-slot")
def block_slot(doctor_id: str, payload: dict, authorization: str | None = Header(None),
               x_demo_role: str | None = Header(None)):
    _require_staff(authorization, x_demo_role)
    return ops.block_slot(doctor_id, payload.get("date", ""), payload.get("time", ""),
                          payload.get("reason", ""))


@router.get("/queue")
def queue(doctor_id: str, date: str, authorization: str | None = Header(None),
          x_demo_role: str | None = Header(None)):
    _require_staff(authorization, x_demo_role)
    return {"doctor_id": doctor_id, "date": date, "queue": ops.get_queue(doctor_id, date)}


@router.post("/queue/{token}/advance")
def q_advance(token: str, authorization: str | None = Header(None),
              x_demo_role: str | None = Header(None)):
    _require_staff(authorization, x_demo_role)
    s, b = ops.queue_action(token, "advance")
    if s >= 400:
        raise HTTPException(s, b.get("error", "error"))
    return b


@router.post("/queue/call-next")
def q_call_next(doctor_id: str, date: str, authorization: str | None = Header(None),
                x_demo_role: str | None = Header(None)):
    _require_staff(authorization, x_demo_role)
    q = ops.get_queue(doctor_id, date)
    waiting = [e for e in q if e["status"] == "waiting"]
    if not waiting:
        raise HTTPException(404, "queue_empty")
    s, b = ops.queue_action(waiting[0]["token"], "call-next")
    return b


@router.post("/queue/{token}/mark-done")
def q_done(token: str, authorization: str | None = Header(None),
           x_demo_role: str | None = Header(None)):
    _require_staff(authorization, x_demo_role)
    s, b = ops.queue_action(token, "mark-done")
    if s >= 400:
        raise HTTPException(s, b.get("error", "error"))
    return b


@router.post("/queue/{token}/mark-no-show")
def q_noshow(token: str, authorization: str | None = Header(None),
             x_demo_role: str | None = Header(None)):
    _require_staff(authorization, x_demo_role)
    s, b = ops.queue_action(token, "mark-no-show")
    if s >= 400:
        raise HTTPException(s, b.get("error", "error"))
    return b


@router.post("/queue/{token}/reorder")
def q_reorder(token: str, payload: dict, authorization: str | None = Header(None),
              x_demo_role: str | None = Header(None)):
    _require_staff(authorization, x_demo_role)
    s, b = ops.queue_action(token, "reorder", payload.get("order", []))
    if s >= 400:
        raise HTTPException(s, b.get("error", "error"))
    return b


@router.post("/check-in")
def checkin(payload: dict, authorization: str | None = Header(None),
            x_demo_role: str | None = Header(None)):
    _require_staff(authorization, x_demo_role)
    s, b = ops.check_in(payload.get("token", ""))
    if s >= 400:
        raise HTTPException(s, b.get("error", "error"))
    return b


@router.get("/cancellations")
def cancellations(date: str | None = None, authorization: str | None = Header(None),
                  x_demo_role: str | None = Header(None)):
    _require_staff(authorization, x_demo_role)
    out = ops.CANCELLATIONS
    if date:
        out = [c for c in out if c["date"] == date]
    return {"cancellations": out}


@router.post("/appointments/{token}/cancel")
def staff_cancel(token: str, payload: dict, authorization: str | None = Header(None),
                 x_demo_role: str | None = Header(None)):
    _require_staff(authorization, x_demo_role)
    s, b = ops.cancel_booking(token, payload.get("reason", ""), "staff")
    if s >= 400:
        raise HTTPException(s, b.get("error", "error"))
    return b


@router.post("/doctors/{doctor_id}/delay")
def set_delay(doctor_id: str, payload: dict, authorization: str | None = Header(None),
              x_demo_role: str | None = Header(None)):
    _require_staff(authorization, x_demo_role)
    return ops.set_delay(doctor_id, int(payload.get("minutes", 0)),
                         payload.get("message", ""), payload.get("language", "en"))


@router.post("/doctors/{doctor_id}/delay/clear")
def clear_delay(doctor_id: str, authorization: str | None = Header(None),
                x_demo_role: str | None = Header(None)):
    _require_staff(authorization, x_demo_role)
    ops.DELAYS.pop(doctor_id, None)
    return {"doctor_id": doctor_id, "delay_minutes": 0}


@router.get("/waitlist")
def ops_waitlist(doctor_id: str | None = None, date: str | None = None,
                 authorization: str | None = Header(None),
                 x_demo_role: str | None = Header(None)):
    _require_staff(authorization, x_demo_role)
    from .. import waitlist as _wl
    return {"waitlist": _wl.list_for_staff(doctor_id, date)}


@router.get("/analytics/daily")
def analytics_daily(date: str, authorization: str | None = Header(None),
                    x_demo_role: str | None = Header(None)):
    _require_staff(authorization, x_demo_role)
    return ops.daily_analytics(date)


@router.get("/analytics/language")
def analytics_language(authorization: str | None = Header(None),
                       x_demo_role: str | None = Header(None),
                       from_date: str | None = Query(None, alias="from"),
                       to_date: str | None = Query(None, alias="to")):
    _require_staff(authorization, x_demo_role)
    return {"by_language": dict(ops.LANGUAGE_COUNTER),
            "events": len(ops.ANALYTICS_EVENTS),
            "note": "In-memory counters for the MVP; Supabase analytics_events when configured."}


@router.get("/analytics/overview")
def analytics_overview(authorization: str | None = Header(None),
                       x_demo_role: str | None = Header(None)):
    _require_staff(authorization, x_demo_role)
    from datetime import date as _d
    today = _d.today().isoformat()
    return {**ops.daily_analytics(today), "by_language": dict(ops.LANGUAGE_COUNTER),
            "total_appointments": len(STORE)}
