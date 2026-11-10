"""Patient support router: KB answers, prepare-visit, post-visit, escalate, glossary."""
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from .. import support as sup
from ..support_kb import GLOSSARY
from .. import gnani

router = APIRouter(prefix="/api/support", tags=["support"])
SAFETY = ("CareVoice explains processes — it does not diagnose or give "
          "treatment advice. For medical concerns, contact a qualified professional.")


@router.post("/ask")
async def ask(payload: dict):
    result = sup.answer_question(payload.get("question", ""), payload.get("language", "en"))
    out = {**result, "safety_notice": SAFETY}
    if payload.get("speak") and result.get("answer"):
        try:
            audio, ctype = await gnani.synthesize(result["answer"], payload.get("language", "en"))
            out["audio_content_type"] = ctype
            return Response(content=audio, media_type=ctype,
                            headers={"X-Support-Status": result["status"]})
        except gnani.GnaniError as e:
            raise HTTPException(e.status, e.detail or e.code)
    return out


@router.post("/prepare-visit")
def prepare_visit(payload: dict):
    return {**sup.prepare_visit(payload.get("doctor_id"), payload.get("speciality")),
            "safety_notice": SAFETY}


@router.get("/post-visit")
def post_visit(appointment_token: str | None = None, record_id: str | None = None):
    return {**sup.post_visit_instructions(appointment_token, record_id),
            "safety_notice": SAFETY}


@router.post("/escalate")
def escalate(payload: dict):
    return {**sup.escalate(payload), "safety_notice": SAFETY}


@router.get("/emergency")
def emergency(language: str = "en"):
    return sup.emergency_payload(language)


@router.post("/emergency")
def emergency_post(payload: dict):
    # Location is used ONLY when the user explicitly grants it (consent_given).
    return sup.emergency_payload(payload.get("language", "en"),
                                 payload.get("latitude"), payload.get("longitude"),
                                 bool(payload.get("consent_given")))


@router.get("/emergency-departments")
def emergency_departments(lat: float | None = None, lng: float | None = None):
    nearby, msg = sup.nearby_departments(lat, lng)
    return {"departments": nearby, "note": msg,
            "disclaimer": "Demo — not a live hospital directory. Only the seeded "
                          "demo hospital is listed."}


@router.get("/glossary")
def glossary(term: str | None = None, language: str = "en"):
    if term:
        t = term.lower()
        hits = {k: (v.get(language) or v["en"]) for k, v in GLOSSARY.items()
                if t in k or t in v["en"].lower()}
        return {"results": hits}
    return {"results": {k: (v.get(language) or v["en"]) for k, v in GLOSSARY.items()}}
