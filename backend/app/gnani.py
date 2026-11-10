"""Real Gnani AI integration — Prisma STT v3.0 and Timbre TTS v2.5.

No key => GnaniError(503, "gnani_not_configured"). Nothing is ever faked:
on any upstream failure the caller gets an error, never a made-up transcript.
The API key is read from config (env var only) and is never logged or returned.
"""
import os

import httpx
from . import config
from .languages import BY_CODE, AUTO_DETECT


def _client() -> httpx.AsyncClient:
    """httpx with trust_env=False: this VM's NO_PROXY contains bracketed
    IPv6 entries ("[::1]") that httpx cannot parse and that break every
    outbound call. Pass the egress proxy explicitly instead."""
    proxy = os.getenv("HTTPS_PROXY") or os.getenv("https_proxy") or None
    # httpx defaults to the certifi bundle, which lacks this VM's egress
    # proxy CA; SSL_CERT_FILE points at the bundle that has it.
    verify = os.getenv("SSL_CERT_FILE") or True
    return httpx.AsyncClient(timeout=config.REQUEST_TIMEOUT_S,
                             trust_env=False, proxy=proxy, verify=verify)


class GnaniError(Exception):
    def __init__(self, status: int, code: str, detail: str = ""):
        super().__init__(detail or code)
        self.status = status
        self.code = code
        self.detail = detail


def _require_key():
    if not config.GNANI_API_KEY:
        raise GnaniError(503, "gnani_not_configured",
                         "Gnani API key is not configured on the server (GNANI_API_KEY).")
    return config.GNANI_API_KEY


def effective_speed(speed: float, senior_mode: bool = False) -> float:
    """Senior / Easy mode always speaks at the slowest supported speed (0.85)."""
    if senior_mode:
        return 0.85
    return min(1.15, max(0.85, float(speed or 1.0)))


def resolve_stt_code(language: str) -> str:
    """Accept 'en', 'en-IN', or 'indic-auto' (code-mix / auto-detect)."""
    if not language:
        return "en-IN"
    if language == AUTO_DETECT or language == "auto":
        return AUTO_DETECT
    if language in BY_CODE:
        return BY_CODE[language]["stt_code"]
    if language in ("ml-IN", "hi-IN", "ta-IN", "te-IN", "kn-IN", "bn-IN", "en-IN"):
        return language
    return "en-IN"


def resolve_tts_code(language: str) -> str:
    """Timbre expects a BCP-47 code (e.g. en-IN), verified live 2026-11-10:
    language "en" alone returns HTTP 400."""
    if not language:
        return "en-IN"
    if language in BY_CODE:
        return BY_CODE[language]["stt_code"]
    if "-" in language:
        return language
    return f"{language}-IN"


async def transcribe(audio_bytes: bytes, filename: str, language: str = "en-IN") -> dict:
    """POST audio to Prisma STT v3.0. Returns {transcript, language_code, model}."""
    key = _require_key()
    if not audio_bytes:
        raise GnaniError(400, "empty_audio", "No audio data received.")
    if len(audio_bytes) > config.MAX_AUDIO_BYTES:
        raise GnaniError(413, "audio_too_large", "Audio file exceeds 10 MB.")
    stt_code = resolve_stt_code(language)
    files = {"audio_file": (filename or "audio.webm", audio_bytes)}
    data = {"language_code": stt_code, "model": config.GNANI_STT_MODEL,
            "format": "transcribe"}
    # Cloudflare in front of api.vachana.ai returns 1010 to non-browser
    # User-Agents (verified live 2026-11-10 with python-urllib).
    headers = {"X-API-Key-ID": key,
               "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"}
    try:
        async with _client() as client:
            resp = await client.post(config.GNANI_STT_URL, files=files,
                                    data=data, headers=headers)
    except httpx.RequestError as e:
        raise GnaniError(502, "gnani_unreachable", f"Could not reach Gnani STT: {e}")
    if resp.status_code != 200:
        raise GnaniError(502, "gnani_stt_error",
                         f"Prisma STT returned HTTP {resp.status_code}.")
    try:
        payload = resp.json()
    except ValueError:
        raise GnaniError(502, "gnani_bad_response", "Prisma returned a non-JSON response.")
    text = (payload.get("transcript") or payload.get("text") or "").strip()
    if not text:
        raise GnaniError(502, "gnani_empty_transcript",
                         "Prisma returned no transcript for this audio.")
    return {"transcript": text,
            "language_code": payload.get("detected_language_code") or payload.get("language_code") or stt_code,
            "model": config.GNANI_STT_MODEL,
            "confidence": payload.get("confidence")}


async def synthesize(text: str, language: str = "en", voice: str | None = None,
                     speed: float = 1.0) -> tuple[bytes, str]:
    """POST text to Timbre TTS. Returns (audio_bytes, content_type)."""
    key = _require_key()
    if not text or not text.strip():
        raise GnaniError(400, "empty_text", "No text to speak.")
    speed = effective_speed(speed)
    lang = resolve_tts_code(language)
    # Verified live 2026-11-10: language must be BCP-47 (en-IN, not "en"),
    # a voice belonging to timbre-v2.5 must be sent, and audio_config must
    # request linear_pcm/wav at 16000 Hz. Without those the API returns 400.
    body = {"text": text.strip(), "model": config.GNANI_TTS_MODEL,
            "language": lang, "speed": speed,
            "audio_config": {"encoding": "linear_pcm", "container": "wav",
                             "sample_rate": 16000}}
    chosen = voice or (BY_CODE.get(lang[:2]) or {}).get("voice") or "Pranav"
    body["voice"] = chosen
    headers = {"X-API-Key-ID": key,
               "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"}
    try:
        async with _client() as client:
            resp = await client.post(config.GNANI_TTS_URL, json=body, headers=headers)
    except httpx.RequestError as e:
        raise GnaniError(502, "gnani_unreachable", f"Could not reach Gnani TTS: {e}")
    if resp.status_code != 200:
        raise GnaniError(502, "gnani_tts_error",
                         f"Timbre TTS returned HTTP {resp.status_code}.")
    ctype = resp.headers.get("content-type", "audio/wav")
    if not resp.content:
        raise GnaniError(502, "gnani_empty_audio", "Timbre returned no audio.")
    return resp.content, ctype
