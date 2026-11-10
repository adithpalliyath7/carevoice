from fastapi import APIRouter
from ..support import emergency_payload

router = APIRouter(prefix="/api/emergency", tags=["emergency"])


@router.get("")
def emergency(language: str = "en"):
    return emergency_payload(language)
