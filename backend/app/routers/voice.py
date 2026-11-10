"""Voice endpoints: Prisma STT, Timbre TTS, rule-based converse."""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import Response, JSONResponse
from .. import gnani, nlu
from ..languages import LANGUAGES, BY_CODE
from ..schemas import ConverseRequest, SpeakRequest
from ..ops import track_language

router = APIRouter(prefix="/api/voice", tags=["voice"])


def _err(e: gnani.GnaniError):
    return JSONResponse(status_code=e.status,
                        content={"error": e.code, "message": e.detail})


@router.get("/languages")
def languages():
    return {"languages": LANGUAGES, "auto_detect": "indic-auto",
            "note": "Code-mixed / code-switched speech is supported via indic-auto."}


@router.post("/transcribe")
async def transcribe(audio_file: UploadFile = File(...),
                     language: str = Form("en-IN")):
    data = await audio_file.read()
    track_language(language, "transcribe")
    try:
        result = await gnani.transcribe(data, audio_file.filename or "audio.webm", language)
    except gnani.GnaniError as e:
        return _err(e)
    return result


@router.post("/speak")
async def speak(req: SpeakRequest):
    track_language(req.language, "tts")
    speed = gnani.effective_speed(req.speed, req.senior_mode)
    try:
        audio, ctype = await gnani.synthesize(req.text, req.language, req.voice, speed)
    except gnani.GnaniError as e:
        return _err(e)
    return Response(content=audio, media_type=ctype)


@router.post("/converse")
async def converse(req: ConverseRequest):
    """Transcript in -> NLU + next prompt + spoken reply (via /speak on demand).
    Returns the parsed intent and the next thing to say; the frontend calls
    /api/voice/speak to vocalise `reply_text` (or replays it slowed)."""
    track_language(req.language, "converse")
    parsed = nlu.parse(req.transcript, req.language, req.session)
    lang = BY_CODE.get(req.language, BY_CODE["en"])
    if parsed["intent"] == "emergency":
        # HARD RULE: emergency bypasses ALL conversation — immediate action only.
        from ..support import emergency_speak_text
        speak_text = emergency_speak_text(req.language)
        return {"emergency": True, "action": "show_emergency_screen",
                "intent": "emergency", "confidence": parsed["confidence"],
                "speak_text": speak_text, "reply_text": speak_text,
                "language": req.language, "senior_mode": req.senior_mode,
                "needs_clarification": False, "clarification_question": None,
                "speciality": None, "date": None, "time": None}
    elif parsed["intent"] == "confirm":
        reply = "Thank you. Please press Confirm on the summary to complete your booking."
    elif parsed["needs_clarification"]:
        reply = parsed["clarification_question"]
    elif parsed["intent"] == "book":
        reply = (f"I found {parsed['speciality']} doctors. Please choose a doctor, "
                 f"then a date and time.")
    elif parsed["intent"] == "repeat":
        reply = "Of course — I will repeat that more slowly."
    else:
        reply = "I understood that. Please continue — choose a doctor, date and time."
    return {"intent": parsed["intent"], "speciality": parsed["speciality"],
            "date": parsed["date"], "time": parsed["time"],
            "confidence": parsed["confidence"],
            "needs_clarification": parsed["needs_clarification"],
            "clarification_question": parsed["clarification_question"],
            "reply_text": reply, "language": req.language,
            "greeting": lang["greeting"]}
