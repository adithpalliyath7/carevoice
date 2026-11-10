"""Feedback collection ONLY. No analysis, no sentiment scoring — the MVP just
stores rating/text so a later voice-feedback-analysis feature has data."""
from fastapi import APIRouter, HTTPException
from .. import feedback_store

router = APIRouter(prefix="/api/feedback", tags=["feedback"])


@router.post("")
def submit(payload: dict):
    rating = payload.get("rating")
    if rating is not None and (not isinstance(rating, int) or not 1 <= rating <= 5):
        raise HTTPException(400, "rating must be an integer 1-5")
    return feedback_store.add(payload)


@router.get("")
def list_all(token: str | None = None):
    return {"feedback": feedback_store.list_all(token),
            "note": "Collection only — no analysis is performed in this MVP."}
