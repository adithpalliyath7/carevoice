"""CareVoice FastAPI app."""
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from . import config
from .routers import (voice, doctors, appointments, emergency, records,
                      support, ops, waitlist, feedback)

app = FastAPI(title="CareVoice", version="0.1.0",
              description="Multilingual AI hospital appointment voice assistant (MVP, demo data).")


def _allowed_origins() -> list[str]:
    """Origins allowed by CORS. ALLOWED_ORIGINS (comma-separated) wins when
    set; otherwise localhost dev origins. Deployed frontends talk to the API
    same-origin, so no production origin needs to be hardcoded here."""
    env = os.getenv("ALLOWED_ORIGINS", "").strip()
    if env:
        return [o.strip() for o in env.split(",") if o.strip()]
    return ["http://localhost:5173", "http://127.0.0.1:5173"]


app.add_middleware(CORSMiddleware, allow_origins=_allowed_origins(),
                   # Vercel preview/production domains (*.vercel.app) when the
                   # frontend is ever served from a different origin.
                   allow_origin_regex=r"https://.*\.vercel\.app",
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(voice.router)
app.include_router(doctors.router)
app.include_router(appointments.router)
app.include_router(emergency.router)
app.include_router(records.router)
app.include_router(support.router)
app.include_router(ops.router)
app.include_router(waitlist.router)
app.include_router(feedback.router)


@app.get("/")
def root():
    return {"service": "CareVoice", "version": "0.1.0", "demo": True,
            "docs": "/docs"}


@app.get("/api/health")
def health():
    return {"status": "ok",
            "gnani_configured": bool(config.GNANI_API_KEY),
            "supabase_configured": bool(config.SUPABASE_URL and config.SUPABASE_SERVICE_ROLE_KEY),
            "demo_mode": config.DEMO_MODE, "version": "0.1.0"}
