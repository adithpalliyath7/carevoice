"""Configuration. Secrets come only from environment variables (or .env)."""
import os
from dotenv import load_dotenv

load_dotenv()

GNANI_API_KEY = os.getenv("GNANI_API_KEY", "").strip() or None
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip() or None
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip() or None
DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() in ("1", "true", "yes")

GNANI_STT_URL = "https://api.vachana.ai/stt/v3"
GNANI_TTS_URL = "https://api.vachana.ai/api/v1/tts/inference"
GNANI_STT_MODEL = "prisma-v3.0"
GNANI_TTS_MODEL = "timbre-v2.5"
MAX_AUDIO_BYTES = 10 * 1024 * 1024  # 10 MB; Prisma also caps clips at ~30 s
REQUEST_TIMEOUT_S = 30.0
