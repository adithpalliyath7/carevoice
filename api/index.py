"""Vercel serverless entrypoint for CareVoice.

Vercel's Python runtime loads the ASGI app from the `app` variable, and
Mangum provides the `handler` for the classic serverless-function path.
Both are exported so either invocation style works. Local uvicorn runs are
unaffected: `uvicorn app.main:app` still loads the app directly.
"""
import os
import sys

# api/index.py lives at <repo>/api/index.py; the FastAPI package is at
# <repo>/backend/app, so the repo root must be on sys.path.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mangum import Mangum  # noqa: E402

from backend.app.main import app  # noqa: E402

handler = Mangum(app, lifespan="off")
