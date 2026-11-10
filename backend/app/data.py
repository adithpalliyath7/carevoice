"""FICTIONAL demo data — clearly labelled, never presented as live availability.

Hospital: "CareVoice General Hospital — Demo", Kochi, Kerala (fictional).
Slots are generated deterministically from doctor_id + date (seeded), so the
same doctor/date always shows the same demo slots. They are labelled
source:"demo_schedule" in every response.
"""
import hashlib
from datetime import date, timedelta

HOSPITAL = {
    "id": "demo-hospital-1",
    "name": "CareVoice General Hospital — Demo",
    "location": "Kochi, Kerala",
    "is_demo": True,
    "phone": "+91 484 000 0000",
    "emergency_phone": "+91 484 000 0001",
}

SPECIALITIES = ["General Physician", "Cardiology", "Dermatology", "Orthopedics",
                "Paediatrics", "Gynaecology", "Neurology", "ENT",
                "Dental", "Ophthalmology"]

DOCTORS = [
    {"id": "dr-anitha-nair", "name": "Dr. Anitha Nair", "speciality": "General Physician",
     "qualification": "MBBS, MD", "experience_years": 12, "languages": ["en", "ml", "hi"],
     "fee_inr": 500, "rating": 4.8, "location": "Kochi"},
    {"id": "dr-rahul-menon", "name": "Dr. Rahul Menon", "speciality": "Cardiology",
     "qualification": "MBBS, MD, DM", "experience_years": 15, "languages": ["en", "ml"],
     "fee_inr": 900, "rating": 4.9, "location": "Kochi"},
    {"id": "dr-meera-iyer", "name": "Dr. Meera Iyer", "speciality": "Cardiology",
     "qualification": "MBBS, MD, DM", "experience_years": 10, "languages": ["en", "ta", "hi"],
     "fee_inr": 850, "rating": 4.7, "location": "Kochi"},
    {"id": "dr-sana-khan", "name": "Dr. Sana Khan", "speciality": "Dermatology",
     "qualification": "MBBS, MD", "experience_years": 8, "languages": ["en", "hi"],
     "fee_inr": 700, "rating": 4.6, "location": "Kochi"},
    {"id": "dr-arun-kumar", "name": "Dr. Arun Kumar", "speciality": "Orthopedics",
     "qualification": "MBBS, MS", "experience_years": 14, "languages": ["en", "ta", "ml"],
     "fee_inr": 800, "rating": 4.8, "location": "Kochi"},
    {"id": "dr-lakshmi-rao", "name": "Dr. Lakshmi Rao", "speciality": "Paediatrics",
     "qualification": "MBBS, MD", "experience_years": 11, "languages": ["en", "te", "hi"],
     "fee_inr": 600, "rating": 4.9, "location": "Kochi"},
    {"id": "dr-priya-sharma", "name": "Dr. Priya Sharma", "speciality": "Gynaecology",
     "qualification": "MBBS, MS", "experience_years": 13, "languages": ["en", "hi"],
     "fee_inr": 750, "rating": 4.7, "location": "Kochi"},
    {"id": "dr-vikram-reddy", "name": "Dr. Vikram Reddy", "speciality": "Neurology",
     "qualification": "MBBS, MD, DM", "experience_years": 16, "languages": ["en", "te"],
     "fee_inr": 1000, "rating": 4.8, "location": "Kochi"},
    {"id": "dr-kavya-shetty", "name": "Dr. Kavya Shetty", "speciality": "ENT",
     "qualification": "MBBS, MS", "experience_years": 9, "languages": ["en", "kn", "ml"],
     "fee_inr": 650, "rating": 4.6, "location": "Kochi"},
    {"id": "dr-farhan-ali", "name": "Dr. Farhan Ali", "speciality": "Dental",
     "qualification": "BDS, MDS", "experience_years": 7, "languages": ["en", "hi", "bn"],
     "fee_inr": 400, "rating": 4.5, "location": "Kochi"},
    {"id": "dr-nisha-gupta", "name": "Dr. Nisha Gupta", "speciality": "Ophthalmology",
     "qualification": "MBBS, MS", "experience_years": 12, "languages": ["en", "hi", "bn"],
     "fee_inr": 700, "rating": 4.7, "location": "Kochi"},
    {"id": "dr-thomas-jacob", "name": "Dr. Thomas Jacob", "speciality": "General Physician",
     "qualification": "MBBS, MD", "experience_years": 18, "languages": ["en", "ml"],
     "fee_inr": 550, "rating": 4.8, "location": "Kochi"},
]

AVG_CONSULT_MINUTES = 15


def get_doctor(doctor_id: str):
    return next((d for d in DOCTORS if d["id"] == doctor_id), None)


def search_doctors(speciality=None, language=None, location=None, q=None):
    out = list(DOCTORS)
    if speciality:
        out = [d for d in out if d["speciality"].lower() == speciality.lower()]
    if language:
        out = [d for d in out if language in d["languages"]]
    if location:
        out = [d for d in out if location.lower() in d["location"].lower()]
    if q:
        ql = q.lower()
        out = [d for d in out if ql in d["name"].lower()
               or ql in d["speciality"].lower()]
    return out


def _seeded(doctor_id: str, day: date) -> int:
    h = hashlib.sha256(f"{doctor_id}|{day.isoformat()}".encode()).hexdigest()
    return int(h[:8], 16)


def generate_slots(doctor_id: str, day: date) -> list[dict]:
    """Deterministic 09:00-17:00, 30-min demo slots. ~70% 'available' by seed."""
    seed = _seeded(doctor_id, day)
    slots = []
    for i in range(16):  # 09:00 .. 16:30
        hour = 9 + i // 2
        minute = 30 * (i % 2)
        available = ((seed >> (i % 24)) & 1) == 1 or i % 3 == 0
        slots.append({"time": f"{hour:02d}:{minute:02d}",
                      "available": bool(available),
                      "source": "demo_schedule"})
    return slots


def next_7_days() -> list[str]:
    today = date.today()
    return [(today + timedelta(days=i)).isoformat() for i in range(7)]
