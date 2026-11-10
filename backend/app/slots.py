"""Slot lookup + waiting-time estimate (labelled estimate, demo data only)."""
from datetime import date
from .data import get_doctor, generate_slots, AVG_CONSULT_MINUTES


def get_slots(doctor_id: str, day: date) -> dict:
    doctor = get_doctor(doctor_id)
    if not doctor:
        return {"error": "doctor_not_found"}
    slots = generate_slots(doctor_id, day)
    booked_before = sum(1 for s in slots if not s["available"])
    return {"doctor_id": doctor_id, "date": day.isoformat(), "slots": slots,
            "source": "demo_schedule",
            "note": "Demo schedule — fictional availability, not live hospital data."}


def waiting_time_minutes(doctor_id: str, day: date, time: str) -> dict:
    """Estimate = queue position (available slots before chosen time that are
    taken in the demo pattern) x average consult length. Always labelled estimate."""
    slots = generate_slots(doctor_id, day)
    position = 0
    for s in slots:
        if s["time"] >= time:
            break
        if not s["available"]:
            position += 1
    est = position * AVG_CONSULT_MINUTES
    return {"estimated_wait_minutes": est, "queue_position": position,
            "avg_consult_minutes": AVG_CONSULT_MINUTES,
            "is_estimate": True,
            "note": "Estimate only, based on the demo schedule."}
