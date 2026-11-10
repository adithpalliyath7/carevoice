# CareVoice — Multilingual AI Hospital Appointment Voice Assistant (MVP)

Book hospital appointments by speaking naturally in Malayalam, Hindi, Tamil,
Telugu, Kannada, Bengali or English — including code-mixed speech. Real Gnani
AI Prisma (STT) + Timbre (TTS) integration, explicit confirmation before any
booking, digital token + QR pass, live queue tracking, an AI Receptionist,
medical records, a hospital staff dashboard, a smart cancellation waitlist,
and Senior / Easy mode.

> **Demo only.** The hospital, all 12 doctors, all slots and all phone
> numbers are **fictional**. Slots are a deterministic demo schedule, labelled
> `source: "demo_schedule"` in every response — never presented as live
> hospital availability.

## Priority table (as set by Adith)

| # | Priority | Module | Status |
|---|----------|--------|--------|
| 1 | Essential | Multilingual AI voice assistant (7 languages, code-mix, repeat/pause/slow-down) | ✅ Built, tested, **Gnani verified live 2026-11-10** (see below) |
| 2 | Essential | Voice-based appointment booking (explicit confirmation) | ✅ Built, tested |
| 3 | Very high | Live token and queue tracking | ✅ Built, tested |
| 4 | Very high | Hospital AI receptionist (greeting, routing, process Q&A, escalation) | ✅ Built, tested |
| 5 | High | Smart cancellation waitlist | ✅ Built, tested |
| 6 | High | Senior citizen accessibility (Easy mode) | ✅ Built, tested |
| 7 | High | Hospital administration dashboard (Ops + analytics) | ✅ Built, tested |
| 8 | Later | Medical document assistant (records / OCR) | ✅ Built, tested — lower priority, finished after 1–7 |
| 9 | Later | Hospital navigation | ❌ Not built — roadmap only |
| 10 | Later | Voice feedback analysis | ❌ Not built — collection-only stub |

## What is NOT in this MVP

- **Hospital navigation (9):** no maps, no indoor directions. The dashboard
  shows a "Coming soon" card only. No fake maps or directions are shown.
- **Voice feedback analysis (10):** `POST /api/feedback` only stores a
  rating/text note. No sentiment or any other analysis is performed.
- **Real Gnani calls: verified live 2026-11-10** through the registered
  Muse connector (`custom.gnani`, key stored in the Secure Vault, never in a
  file). Timbre spoke a test sentence and Prisma transcribed that same audio:
  transcript `"Namaste, this is CareVoice. Your appointment is confirmed for
  tomorrow at 10:00."`, model `prisma-v3.0`, detected `en-IN`, under 1 s.
  The backend code path itself (`app/gnani.py`) was run against the live API
  the same day and returned the same transcript. To run the backend yourself,
  put the key in `backend/.env` — the stored connector credential cannot be
  read back out, so it cannot fill `.env` for you.
- **Real payments, SMS/email reminders, real auth:** none. Reminders are
  in-app lists; staff login is demo-only (see below).

## Safety

**CareVoice explains processes — it does not diagnose or give treatment
advice. For medical concerns, contact a qualified professional.**

- Support answers come ONLY from a curated local knowledge base
  (`backend/app/support_kb.py`). Anything else returns `not_covered` +
  "ask your doctor" — medical advice is never invented.
- Post-visit instructions are shown ONLY when doctor-provided notes exist on
  file; otherwise the safe fallback is shown.
- OCR text is labelled "unverified — check the original" everywhere.

### Emergency safety

- CareVoice **does not diagnose, does not delay care, and does not dispatch
  ambulances**. It connects the user to **108** (ambulance) and **112**
  (national emergency, real public numbers in India) and the hospital casualty
  department (demo number, labelled demo).
- An emergency transcript bypasses ALL conversation: no clarifying questions,
  no symptom questions, no booking flow. The first response is immediate
  action, in the user's language, spoken slowly and calmly via Timbre.
- The emergency screen has three states: (1) huge red SOS + call buttons,
  (2) "You have requested help — stay on the call" (only after the user taps
  Call/SOS — responders are never claimed to be dispatched), (3) nearby
  emergency departments — shown ONLY with the user's location permission and
  only the seeded demo hospital, with straight-line distance labelled as an
  estimate. No responder names, ETAs or invented hospitals, ever.
- Location is used only when the user explicitly grants it (`consent_given`),
  never auto-tracked, never stored.

## Architecture

```
carevoice/
  backend/  FastAPI (app/main.py) — routers: voice, doctors, appointments,
            emergency, records, support, ops, waitlist, feedback
            app/gnani.py (Prisma STT / Timbre TTS), app/nlu.py (rule-based,
            no fake AI), app/data.py + app/slots.py (demo schedule),
            app/bookings.py, app/ops.py, app/records.py, app/support.py,
            app/support_kb.py, app/waitlist.py, app/storage.py
  frontend/ React + Vite + Tailwind v4 — LanguagePicker flow, VoiceAssistant
            (MediaRecorder → Prisma), BookingFlow, TokenCard (QR), Records,
            Support (AI Receptionist), Ops (staff dashboard), Emergency (3-state)
  supabase/ schema.sql + seed.sql + README.md
  scripts/  check-gnani.py
```

## Quick start

### Backend
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then set GNANI_API_KEY (see below)
uvicorn app.main:app --reload --port 8000
# Health: curl http://localhost:8000/api/health
# Docs:  http://localhost:8000/docs
```

### Frontend
```bash
cd frontend
npm install
cp .env.example .env   # VITE_API_URL=http://localhost:8000
npm run dev            # http://localhost:5173
npm run build          # production build
```

### Tests
```bash
cd backend && .venv/bin/python -m pytest tests/ -q
```
49 tests, no network, no Gnani key needed. Gnani-dependent paths are tested
only for their honest 503 behaviour; live-call tests are skipped without a key.

## Gnani API key setup

1. Get a key from Gnani AI (Prisma STT + Timbre TTS).
2. Put it **only** in `backend/.env`: `GNANI_API_KEY=<your key>`.
   It is never in the frontend, never logged, never printed, never committed
   (`.env` is git-ignored).
3. Verify it: `python3 scripts/check-gnani.py` (reads the key from env only,
   calls Timbre once, prints only the HTTP status — never the key).
4. Without a key, `/api/voice/transcribe` and `/api/voice/speak` return
   `503 {"error":"gnani_not_configured"}` and the UI shows a clear banner.

Endpoints used (verified live 2026-11-10): Prisma STT v3.0 `POST https://api.vachana.ai/stt/v3`
(header `X-API-Key-ID`, multipart `audio_file`, `language_code`, `model=prisma-v3.0`,
`format=transcribe`, audio ≤ 30 s); Timbre TTS `POST https://api.vachana.ai/api/v1/tts/inference`
(JSON `{text, voice, model: timbre-v2.5, language, speed 0.85–1.15, audio_config}`).
STT codes: `ml-IN, hi-IN, ta-IN, te-IN, kn-IN, bn-IN, en-IN`, plus `indic-auto`
for code-mixed speech. TTS codes are BCP-47 too (`en-IN`, not `en` — `en`
returns HTTP 400). Three Timbre details found by live testing: the language
must be BCP-47, a voice belonging to timbre-v2.5 must be sent, and
`audio_config` must be `{"encoding":"linear_pcm","container":"wav",
"sample_rate":16000}` (returns a 16 kHz WAV). Cloudflare in front of the API
returns 1010 to non-browser User-Agents, so the backend sends a browser
User-Agent. Verified timbre-v2.5 voices: English `Pranav`, Malayalam `Reshma`,
Hindi `Deepak`, Tamil `Asmita`, Telugu `Suhana`, Kannada `Saanvi`, Bengali
`Kirra`. (Kaveri is an English voice, not Tamil.)

## Supabase setup

See `supabase/README.md`. Run `supabase/schema.sql` then `supabase/seed.sql`
in the SQL editor; set `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` in
`backend/.env`. The MVP runs fully without Supabase (in-memory store).

## Records / OCR setup

Uploads live under `backend/storage/records/<id>/` (git-ignored local disk by
default; Supabase Storage when configured — see `app/storage.py`).
OCR: install Tesseract for image OCR (`apt install tesseract-ocr`); PDF text
uses `pypdf`. If Tesseract is absent, uploads still work with
`ocr_status: "unavailable"` and `extracted_text: ""` — the API never claims
OCR succeeded when it didn't. Share links last 24h (`GET /api/records/shared/<token>`,
410 when expired). Downloads require the `X-Patient-Phone` header to match
the record.

## Staff demo logins (DEMO ONLY)

- `receptionist@demo` / `demo1234` — queue, check-in, walk-ins, delays, cancellations
- `admin@demo` / `demo1234` — plus availability management

Roles are carried on the `X-Demo-Role` header in the MVP, with `POST /api/ops/login`
returning a demo token. **Production-auth warning: real JWT / Supabase Auth
must replace this before any production use. Patients get 403 on `/api/ops/*`.**

## Key endpoints

| Endpoint | Notes |
|---|---|
| `GET /api/health` | `{status, gnani_configured, supabase_configured, demo_mode, version}` — no key value |
| `POST /api/voice/transcribe` | multipart audio → Prisma transcript |
| `POST /api/voice/speak` | JSON text → Timbre audio; `senior_mode` forces 0.85× |
| `POST /api/voice/converse` | transcript → NLU intent + reply; emergency returns `{emergency:true, action:"show_emergency_screen"}` |
| `GET /api/doctors`, `GET /api/doctors/{id}/slots?date=` | demo schedule, `source:"demo_schedule"` |
| `POST /api/appointments` | `confirmed:false` → 422 `confirmation_required`; `confirmed:true` → token `CV-YYYYMMDD-XXXX` + QR payload |
| `GET /api/appointments/{token}`, `.../queue-position`, `.../check-in`, `PATCH .../reschedule`, `POST .../cancel` | |
| `POST /api/waitlist`, `GET /api/waitlist/{id}`, `.../accept` (confirm required), `.../decline` | 30-min offers, auto-roll on cancel/decline/expiry |
| `POST /api/support/ask`, `/prepare-visit`, `/post-visit`, `/escalate`, `GET /api/support/glossary`, `/emergency` | KB-only answers; `not_covered` when unknown |
| `POST /api/support/emergency` | `{language, latitude?, longitude?, consent_given}` — contacts-only without consent |
| `GET /api/support/emergency-departments?lat=&lng=` | demo hospital only, distance = straight-line estimate |
| `POST /api/records/upload`, `GET /api/records`, `GET /api/records/{id}/download`, `POST .../share`, `GET /api/records/shared/{token}`, `GET /api/records/search/voice` | |
| `POST /api/records/reminders`, `GET /api/records/reminders`, `POST /api/records/reminders/{id}/speak` | in-app only, no SMS/email |
| `POST /api/ops/login`, `/api/ops/*` | staff only; analytics `/analytics/daily`, `/analytics/language`, `/analytics/overview` |
| `POST /api/feedback` | collection only — rating 1–5 + note, no analysis |

## Deployment

### Vercel (public deployment)

The repo is ready for Vercel (see `vercel.json` at the root): one project,
static frontend from `frontend/dist` + Python serverless function `api/index.py`
(Mangum wrapper around the FastAPI app) serving `/api/*` on the same domain.

1. In Vercel, import the `adithpalliyath7/carevoice` repo. Vercel reads
   `vercel.json` for the build command (`cd frontend && npm run build`),
   install command, output directory (`frontend/dist`) and rewrites — no
   framework preset or Root Directory change needed.
2. Set these environment variables in the Vercel project (Production):
   `GNANI_API_KEY` (required for voice; get one at https://app.gnani.ai —
   without it `/api/voice/*` returns `503 gnani_not_configured`),
   and optionally `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` for durable
   storage, and `ALLOWED_ORIGINS` (comma-separated) if the frontend is ever
   served from another origin.
3. Deploy. Voice, booking, queue and waitlist run serverless.

**Vercel limitation, read first:** serverless functions are stateless — the
backend's in-memory store (appointments, queue, waitlist, records metadata,
uploaded files under `/tmp`) resets between invocations and cold starts, so a
booking made on one invocation may not be visible on the next. For a
production deployment, configure Supabase (schema in `supabase/`) so data
persists. Until then the deployment is a working demo, not a durable system.

- **Backend:** any Python host (Render/Railway/a VPS): `pip install -r requirements.txt`,
  set `GNANI_API_KEY` (+ Supabase vars) as environment secrets, run
  `uvicorn app.main:app --host 0.0.0.0 --port 8000`. Restrict CORS
  (`allow_origins` in `app/main.py`, currently Vite `:5173`) to the real frontend origin.
- **Frontend:** `npm run build`, serve `dist/` statically (Netlify/Vercel/any
  static host) with `VITE_API_URL` pointing at the backend.
- **Supabase:** run the SQL files; add RLS policies + Supabase Auth before
  real patient data.

## Honest limits

- Gnani live calls are **verified** (see above) for short English audio only.
  Other languages and longer clips are untested through the live key so far.
- Voice transcription quality, TTS voices, and the 30-second Prisma limit are
  Gnani-side behaviours; the backend enforces the size limit and surfaces
  Gnani errors as 502s with no fake fallback.
- All data is in-memory unless Supabase is configured; restarting the backend
  clears appointments, records metadata, waitlist and queue state.
- No real phone calls are placed by the app — `tel:` links open the device dialler.
