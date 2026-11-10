"""In-memory feedback store (collection only)."""
from datetime import datetime, timezone

FEEDBACK: list[dict] = []


def add(payload: dict) -> dict:
    item = {"id": f"FB-{len(FEEDBACK) + 1:04d}",
            "appointment_token": payload.get("token"),
            "rating": payload.get("rating"),
            "note": payload.get("note"),
            "voice_note": payload.get("voice_note"),
            "created_at": datetime.now(timezone.utc).isoformat()}
    FEEDBACK.append(item)
    return item


def list_all(token: str | None = None):
    if token:
        return [f for f in FEEDBACK if f.get("appointment_token") == token]
    return list(FEEDBACK)
