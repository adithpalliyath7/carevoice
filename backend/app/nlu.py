"""Rule-based multilingual intent parser over a transcript.

NO fake AI: only keyword/regex matching in English + transliterated forms of
the 7 languages. Low confidence => ask the user to repeat; never guess a booking.
"""
import re
from datetime import date, timedelta

SPECIALITIES = {
    "cardiology": ["cardiolog", "heart", "hruday", "hriday", "cardiac", "இதய", "ഹൃദയ", "గుండె", "ಹೃದಯ", "হৃদ"],
    "dermatology": ["dermatolog", "skin", "charm", "charmam", "தோல்", "ചർമ്മ", "చర్మ", "ಚರ್ಮ", "চামড়া"],
    "orthopedics": ["orthoped", "ortho", "bone", "joint", "elumb", "எலும்பு", "അസ്ഥി", "ఎముక", "ಮೂಳೆ", "হাড়"],
    "paediatrics": ["paediatric", "pediatric", "child", "kids", "bacha", "குழந்தை", "കുട്ടി", "పిల్ల", "ಮಗು", "শিশু"],
    "gynaecology": ["gynaecolog", "gynecolog", "gynae", "women", "mahila", "பெண்", "സ്ത്രീ", "స్త్రీ", "ಮಹಿಳೆ", "মহিলা"],
    "neurology": ["neurolog", "neuro", "brain", "mastishk", "மூளை", "തലച്ചോറ്", "మెదడు", "ಮೆದುಳು", "মস্তিষ্ক"],
    "ent": ["ent", "ear", "nose", "throat", "kaath", "காது", "ചെവി", "చెవి", "ಕಿವಿ", "কান"],
    "general physician": ["general physician", "physician", "fever", "bukhar", "காய்ச்சல்", "പനി", "జ్వరం", "ಜ್ವರ", "জ্বর"],
    "dental": ["dental", "dentist", "tooth", "teeth", "daant", "பல்", "പല്ല്", "పన్ను", "ಹಲ್ಲು", "দাঁত"],
    "ophthalmology": ["ophthalmolog", "eye", "aankh", "கண்", "കണ്ണ്", "కన్ను", "ಕಣ್ಣು", "চোখ"],
}
EMERGENCY_WORDS = [
    # English
    "emergency", "ambulance", "chest pain", "breathless", "breathing problem",
    "can't breathe", "cannot breathe", "unconscious", "heavy bleeding", "bleeding",
    "accident", "help me", "medical emergency",
    # Hindi (transliterated)
    "aapatkaaleen", "aapatkal", "madad", "saans", "seene mein dard", "khoon",
    "aap composing".replace(" composing", ""),
    # Malayalam (transliterated)
    "aatyavasam", "sahayam", "shwasam", "nenjil vedana", "raktham",
    # Tamil (transliterated)
    "avasara", "udhavi", "moochu", "nenjil vali", "raththam",
    # Telugu (transliterated)
    "atyavasaram", "sahayam", "shwasa", "gundelo noppi", "raktam",
    # Kannada (transliterated)
    "turtu", "sahaya", "usiru", "ede noppu", "rakta",
    # Bengali (transliterated)
    "joruri", "sahajjo", "shwas", "buke betha", "rokto",
    # Script forms
    "आपातकाल", "मदद", "അടിയന്തര", "സഹായം", "அவசர", "உதவி",
    "అత్యవసర", "సహాయం", "ತುರ್ತು", "ಸಹಾಯ", "জরুরি", "সাহায্য",
]
YES_WORDS = {"yes", "yeah", "yep", "correct", "confirm", "haan", "ha", "seri", "sheri",
             "aama", "aam", "avunu", "haudu", "haane", "hmm"}
NO_WORDS = {"no", "nahi", "nope", "cancel", "illa", "alla", "kadhe", "ledu", "bedi", "na"}
REPEAT_WORDS = ["repeat", "again", "slow", "slowly", "phir se", "meendum", "veendum",
                "malli", "matte", "abar"]
DATE_WORDS = {"today": 0, "tomorrow": 1, "day after tomorrow": 2,
              "innu": 0, "naale": 1, "aaj": 0, "kal": 1, "iniki": 0, "naalai": 1,
              "repu": 1, "naale": 1, "naale": 1}
WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def _find_speciality(text: str):
    for spec, keys in SPECIALITIES.items():
        for k in keys:
            if k in text:
                return spec
    return None


def _find_date(text: str):
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", text)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3))).isoformat()
        except ValueError:
            return None
    m = re.search(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})", text)
    if m:
        try:
            return date(int(m.group(3)), int(m.group(2)), int(m.group(1))).isoformat()
        except ValueError:
            return None
    for word, delta in DATE_WORDS.items():
        if word in text:
            return (date.today() + timedelta(days=delta)).isoformat()
    for i, wd in enumerate(WEEKDAYS):
        if wd in text:
            today = date.today()
            delta = (i - today.weekday()) % 7 or 7
            return (today + timedelta(days=delta)).isoformat()
    return None


def _find_time(text: str):
    m = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b", text)
    if m:
        h = int(m.group(1)) % 12 + (12 if m.group(3) == "pm" else 0)
        return f"{h:02d}:{m.group(2) or '00'}"
    m = re.search(r"\b([01]?\d):([0-5]\d)\b", text)
    if m:
        return f"{int(m.group(1)):02d}:{m.group(2)}"
    return None


def parse(transcript: str, language: str = "en", session: dict | None = None) -> dict:
    """Returns {intent, speciality, date, time, confidence, needs_clarification,
    clarification_question}. Confidence is a coarse 0..1 heuristic."""
    session = session or {}
    text = (transcript or "").strip().lower()
    if not text:
        return {"intent": "unknown", "speciality": None, "date": None, "time": None,
                "confidence": 0.0, "needs_clarification": True,
                "clarification_question": "I could not hear you clearly. Please repeat."}
    words = set(re.findall(r"[a-z]+", text))
    if any(w in text for w in EMERGENCY_WORDS):
        return {"intent": "emergency", "speciality": None, "date": None, "time": None,
                "confidence": 0.9, "needs_clarification": False, "clarification_question": None}
    if words & YES_WORDS and session.get("awaiting_confirmation"):
        return {"intent": "confirm", "speciality": session.get("speciality"),
                "date": session.get("date"), "time": session.get("time"),
                "confidence": 0.9, "needs_clarification": False, "clarification_question": None}
    if words & NO_WORDS and session.get("awaiting_confirmation"):
        return {"intent": "cancel", "speciality": None, "date": None, "time": None,
                "confidence": 0.8, "needs_clarification": False, "clarification_question": None}
    if any(w in text for w in REPEAT_WORDS):
        return {"intent": "repeat", "speciality": None, "date": None, "time": None,
                "confidence": 0.9, "needs_clarification": False, "clarification_question": None}
    if "reschedul" in text or "change" in text and "appointment" in text:
        return {"intent": "reschedule", "speciality": None, "date": _find_date(text),
                "time": _find_time(text), "confidence": 0.7,
                "needs_clarification": False, "clarification_question": None}
    if "cancel" in text and "appointment" in text:
        return {"intent": "cancel", "speciality": None, "date": None, "time": None,
                "confidence": 0.8, "needs_clarification": False, "clarification_question": None}
    spec = _find_speciality(text)
    d, t = _find_date(text), _find_time(text)
    if spec or "book" in text or "appointment" in text or "doctor" in text:
        conf = 0.85 if spec else 0.5
        needs = spec is None
        return {"intent": "book" if spec else "search", "speciality": spec,
                "date": d, "time": t, "confidence": conf,
                "needs_clarification": needs,
                "clarification_question": ("Which speciality do you need? For example, "
                    "cardiology, dermatology, or general physician.") if needs else None}
    return {"intent": "unknown", "speciality": None, "date": d, "time": t,
            "confidence": 0.2, "needs_clarification": True,
            "clarification_question": ("I did not understand. Please say the speciality, "
             "for example 'book a cardiology appointment tomorrow'.")}
