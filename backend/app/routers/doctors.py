from datetime import date
from fastapi import APIRouter, HTTPException, Query
from ..data import DOCTORS, HOSPITAL, SPECIALITIES, get_doctor, search_doctors, next_7_days
from ..ops import effective_slots, DELAYS, get_availability

router = APIRouter(prefix="/api/doctors", tags=["doctors"])


@router.get("")
def list_doctors(speciality: str | None = None, language: str | None = None,
                 location: str | None = None, q: str | None = None):
    return {"hospital": HOSPITAL, "specialities": SPECIALITIES,
            "doctors": search_doctors(speciality, language, location, q),
            "demo": True}


@router.get("/{doctor_id}")
def doctor_detail(doctor_id: str):
    d = get_doctor(doctor_id)
    if not d:
        raise HTTPException(404, "doctor_not_found")
    delay = DELAYS.get(doctor_id)
    return {**d, "delay_minutes": delay["delay_minutes"] if delay else 0,
            "delay_announcement": delay["message"] if delay else None,
            "availability": get_availability(doctor_id),
            "next_7_days": next_7_days(), "demo": True}


@router.get("/{doctor_id}/slots")
def doctor_slots(doctor_id: str, date_str: str = Query(..., alias="date")):
    if not get_doctor(doctor_id):
        raise HTTPException(404, "doctor_not_found")
    try:
        day = date.fromisoformat(date_str)
    except ValueError:
        raise HTTPException(400, "invalid_date")
    delay = DELAYS.get(doctor_id)
    return {"doctor_id": doctor_id, "date": date_str,
            "slots": effective_slots(doctor_id, day),
            "source": "demo_schedule",
            "delay_minutes": delay["delay_minutes"] if delay else 0,
            "delay_announcement": delay["message"] if delay else None,
            "note": "Demo schedule — fictional availability, not live hospital data."}
