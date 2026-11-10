"""AI Patient Support — rule/template-based, no LLM, no diagnosis.

Every answer comes from the curated local knowledge base (support_kb) or from
doctor-provided notes on file. Anything else => not_covered + ask-your-doctor.
"""
import re
import uuid
from datetime import datetime, timezone
from . import support_kb as kb
from .data import HOSPITAL
from .bookings import get_booking

ESCALATIONS: dict[str, dict] = {}


def answer_question(question: str, language: str = "en") -> dict:
    q = (question or "").strip().lower()
    if not q:
        return {"answer": None, "status": "not_covered",
                "suggested_action": "ask_doctor",
                "questions_to_ask": kb.QUESTIONS_TO_ASK}
    # Glossary hit first
    for term, translations in kb.GLOSSARY.items():
        if term in q or q in term:
            return {"answer": translations.get(language) or translations["en"],
                    "status": "answered", "source": f"glossary:{term}",
                    "suggested_action": None, "questions_to_ask": []}
    best, best_score = None, 0
    for entry in kb.FAQ:
        score = sum(1 for kw in entry["keywords"] if kw in q)
        if score > best_score:
            best, best_score = entry, score
    if best and best_score >= 1:
        return {"answer": best["answer_en"], "status": "answered",
                "source": "faq", "suggested_action": None, "questions_to_ask": []}
    return {"answer": None, "status": "not_covered",
            "suggested_action": "ask_doctor",
            "questions_to_ask": kb.QUESTIONS_TO_ASK,
            "message": "This question is not covered by CareVoice's information. "
                       "Please ask your doctor — do not rely on general advice."}


def prepare_visit(doctor_id=None, speciality=None) -> dict:
    from .data import get_doctor
    spec = speciality
    doctor = get_doctor(doctor_id) if doctor_id else None
    if doctor:
        spec = doctor["speciality"]
    key = (spec or "").lower()
    checklist = kb.PREP_BY_SPECIALITY.get(key, kb.GENERIC_PREP)
    return {"doctor": doctor["name"] if doctor else None, "speciality": spec,
            "prep_checklist": checklist, "questions_to_ask": kb.QUESTIONS_TO_ASK,
            "label": "Preparation aid — not medical advice."}


def post_visit_instructions(appointment_token=None, record_id=None) -> dict:
    """ONLY doctor-provided notes. Never generated."""
    notes = None
    if appointment_token:
        appt = get_booking(appointment_token)
        if appt:
            notes = appt.get("doctor_notes")
    if record_id:
        from .records import RECORDS
        rec = RECORDS.get(record_id)
        if rec:
            notes = rec.get("doctor_notes")
    if notes:
        return {"status": "on_file", "instructions": notes,
                "source": "doctor_notes",
                "note": "These instructions were provided by your doctor."}
    return {"status": "none_on_file", "instructions": None,
            "source": None,
            "note": "No post-visit instructions on file — follow the printed "
                    "discharge / prescription sheet and contact the hospital if unsure."}


def escalate(payload: dict) -> dict:
    concern = (payload.get("concern") or "").lower()
    severity = payload.get("severity", "routine")
    if any(k in concern for k in kb.EMERGENCY_KEYWORDS):
        severity = "emergency"
    ref = f"ESC-{uuid.uuid4().hex[:8].upper()}"
    rec = {"reference_id": ref, "patient_name": payload.get("patient_name"),
           "patient_phone": payload.get("patient_phone"), "concern": payload.get("concern"),
           "severity": severity, "appointment_token": payload.get("appointment_token"),
           "language": payload.get("language", "en"),
           "created_at": datetime.now(timezone.utc).isoformat()}
    ESCALATIONS[ref] = rec
    if severity == "emergency":
        next_step = ("EMERGENCY: call 108 (ambulance) or 112 now, or go directly to "
                     "casualty. Do not wait for a callback.")
    elif severity == "urgent":
        next_step = ("Urgent: go to OPD / casualty or call the hospital. "
                     "Demo: no real call is placed by CareVoice.")
    else:
        next_step = ("Routine: a nurse / coordinator will call you back. "
                     "Demo: no real call is placed by CareVoice.")
    return {**rec, "next_step": next_step}


EMERGENCY_SPEAK = {
    "en": "Emergency. Please stay calm. Call 108 for an ambulance, or 112. Stay on the line.",
    "hi": "आपातकाल। कृपया शांत रहें। एम्बुलेंस के लिए 108 पर कॉल करें, या 112 पर। लाइन पर बने रहें।",
    "ml": "അടിയന്തരാവസ്ഥ. ദയവായി ശാന്തരായിരിക്കുക. ആംബുലൻസിന് 108 എന്ന നമ്പറിൽ വിളിക്കുക, അല്ലെങ്കിൽ 112.",
    "ta": "அவசரநிலை. தயவுசெய்து அமைதியாக இருங்கள். ஆம்புலன்சுக்கு 108 ஐ அழைக்கவும், அல்லது 112.",
    "te": "అత్యవసర పరిస్థితి. దయచేసి ప్రశాంతంగా ఉండండి. అంబులెన్స్ కోసం 108 కి కాల్ చేయండి, లేదా 112.",
    "kn": "ತುರ್ತು ಪರಿಸ್ಥಿತಿ. ದಯವಿಟ್ಟು ಶಾಂತವಾಗಿರಿ. ಆಂಬ್ಯುಲೆನ್ಸ್‌ಗಾಗಿ 108 ಗೆ ಕರೆ ಮಾಡಿ, ಅಥವಾ 112.",
    "bn": "জরুরি অবস্থা। দয়া করে শান্ত থাকুন। অ্যাম্বুলেন্সের জন্য 108-এ কল করুন, অথবা 112।",
}

# Demo hospital coordinates (Kochi, Kerala) — fictional hospital, real city.
DEMO_HOSPITAL_LAT, DEMO_HOSPITAL_LNG = 9.9312, 76.2673


def emergency_speak_text(language: str = "en") -> str:
    return EMERGENCY_SPEAK.get(language, EMERGENCY_SPEAK["en"])


def _haversine_km(lat1, lng1, lat2, lng2) -> float:
    import math
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return round(2 * r * math.asin(math.sqrt(a)), 1)


def nearby_departments(lat=None, lng=None):
    """ONLY the seeded demo hospital — never an invented directory."""
    if lat is None or lng is None:
        return [], "Enable location to see nearby departments."
    dist = _haversine_km(lat, lng, DEMO_HOSPITAL_LAT, DEMO_HOSPITAL_LNG)
    return [{"name": HOSPITAL["name"], "location": HOSPITAL["location"],
             "casualty_phone": HOSPITAL["emergency_phone"],
             "latitude": DEMO_HOSPITAL_LAT, "longitude": DEMO_HOSPITAL_LNG,
             "distance_km": dist, "distance_note": "Straight-line estimate only.",
             "is_demo": True,
             "maps_url": "https://www.google.com/maps/search/?api=1&query=9.9312,76.2673"}], ""


def emergency_payload(language: str = "en", latitude=None, longitude=None,
                      consent_given: bool = False) -> dict:
    base = {"is_demo": True,
            "hospital": {"name": HOSPITAL["name"], "location": HOSPITAL["location"],
                         "casualty_phone": HOSPITAL["emergency_phone"],
                         "note": "Demo hospital number — fictional."},
            "ambulance": "108", "national_emergency": "112",
            "note": "108 and 112 are real public emergency numbers in India. "
                    "The hospital number above is fictional (demo).",
            "instructions": "Call 108 or 112 now, or go directly to the nearest "
                            "hospital casualty department. Stay on the line and follow "
                            "the operator's instructions.",
            "calm_guidance": "Speak calmly. Stay on the line. Help is on the way once "
                             "you have called — do not hang up.",
            "speak_text": emergency_speak_text(language),
            "language": language,
            "location_consent": bool(consent_given)}
    # No consent / no location => contacts only, never a nearby list.
    if not consent_given or latitude is None or longitude is None:
        base["nearby_departments"] = []
        base["nearby_note"] = "Enable location to see nearby departments."
        return base
    nearby, note = nearby_departments(latitude, longitude)
    base["nearby_departments"] = nearby
    base["nearby_note"] = note
    return base
