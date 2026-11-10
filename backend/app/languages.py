"""The 7 supported languages. TTS codes are BCP-47 (en-IN etc.) and voices are
from the verified timbre-v2.5 list in the Pipecat Gnani docs, confirmed live
2026-11-10: en Pranav, ml Reshma, hi Deepak, ta Asmita, te Suhana, kn Saanvi,
bn Kirra. (Kaveri is an English voice, not Tamil.)"""
LANGUAGES = [
    {"code": "en", "stt_code": "en-IN", "tts_code": "en-IN",
     "name": "English", "native": "English",
     "greeting": "Hello, I am CareVoice. How can I help you book an appointment today?",
     "voice": "Pranav"},
    {"code": "ml", "stt_code": "ml-IN", "tts_code": "ml-IN",
     "name": "Malayalam", "native": "മലയാളം",
     "greeting": "നമസ്കാരം, ഞാൻ കെയർവോയ്‌സ് ആണ്. അപ്പോയിന്റ്മെന്റ് ബുക്ക് ചെയ്യാൻ എങ്ങനെ സഹായിക്കാം?",
     "voice": "Reshma"},
    {"code": "hi", "stt_code": "hi-IN", "tts_code": "hi-IN",
     "name": "Hindi", "native": "हिन्दी",
     "greeting": "नमस्ते, मैं CareVoice हूँ। आज अपॉइंटमेंट बुक करने में कैसे मदद करूँ?",
     "voice": "Deepak"},
    {"code": "ta", "stt_code": "ta-IN", "tts_code": "ta-IN",
     "name": "Tamil", "native": "தமிழ்",
     "greeting": "வணக்கம், நான் CareVoice. இன்று அப்பாயிண்ட்மெண்ட் பதிவு செய்ய எப்படி உதவலாம்?",
     "voice": "Asmita"},
    {"code": "te", "stt_code": "te-IN", "tts_code": "te-IN",
     "name": "Telugu", "native": "తెలుగు",
     "greeting": "నమస్కారం, నేను CareVoice. ఈరోజు అపాయింట్‌మెంట్ బుక్ చేయడంలో ఎలా సహాయం చేయగలను?",
     "voice": "Suhana"},
    {"code": "kn", "stt_code": "kn-IN", "tts_code": "kn-IN",
     "name": "Kannada", "native": "ಕನ್ನಡ",
     "greeting": "ನಮಸ್ಕಾರ, ನಾನು CareVoice. ಇಂದು ಅಪಾಯಿಂಟ್‌ಮೆಂಟ್ ಬುಕ್ ಮಾಡಲು ಹೇಗೆ ಸಹಾಯ ಮಾಡಲಿ?",
     "voice": "Saanvi"},
    {"code": "bn", "stt_code": "bn-IN", "tts_code": "bn-IN",
     "name": "Bengali", "native": "বাংলা",
     "greeting": "নমস্কার, আমি CareVoice। আজ অ্যাপয়েন্টমেন্ট বুক করতে কীভাবে সাহায্য করব?",
     "voice": "Kirra"},
]
BY_CODE = {l["code"]: l for l in LANGUAGES}
BY_STT = {l["stt_code"]: l for l in LANGUAGES}
# Code-mixed / auto-detect: Prisma v3 supports code-switching; "indic-auto" is
# passed through when the client asks for auto detection.
AUTO_DETECT = "indic-auto"
