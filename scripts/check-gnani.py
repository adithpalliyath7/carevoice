#!/usr/bin/env python3
"""Check Gnani credentials without printing the key.

Reads GNANI_API_KEY from the environment only (or backend/.env). Calls Timbre
TTS with a short text and reports the HTTP status. Exit 0 = key works,
non-zero = not configured / call failed. Never prints the key.
Usage: GNANI_API_KEY=... python3 scripts/check-gnani.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "backend", ".env"))
key = os.getenv("GNANI_API_KEY", "").strip()
if not key:
    print("NOT CONFIGURED: GNANI_API_KEY is not set. Set it in backend/.env "
          "(never commit .env) or export it before running.")
    sys.exit(2)

import httpx  # noqa: E402

resp = httpx.post(
    "https://api.vachana.ai/api/v1/tts/inference",
    json={"text": "Namaste. This is a CareVoice test.",
          "model": "timbre-v2.5", "language": "en-IN", "voice": "Pranav",
          "speed": 1.0,
          "audio_config": {"encoding": "linear_pcm", "container": "wav",
                           "sample_rate": 16000}},
    headers={"X-API-Key-ID": key,
             "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"},
    timeout=30)
print(f"Timbre TTS HTTP {resp.status_code}, {len(resp.content)} bytes received.")
sys.exit(0 if resp.status_code == 200 else 1)
