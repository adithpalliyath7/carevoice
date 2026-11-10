"""Pydantic request/response models."""
from __future__ import annotations
from datetime import date
from typing import Optional
from pydantic import BaseModel, Field


class ConverseRequest(BaseModel):
    transcript: str
    language: str = "en"
    session: dict = Field(default_factory=dict)
    senior_mode: bool = False


class SpeakRequest(BaseModel):
    text: str
    language: str = "en"
    voice: Optional[str] = None
    speed: float = Field(default=1.0, ge=0.85, le=1.15)
    senior_mode: bool = False


class AppointmentCreate(BaseModel):
    doctor_id: str
    date: str            # YYYY-MM-DD
    time: str            # HH:MM (24h)
    patient_name: str
    patient_phone: str
    patient_age: Optional[int] = None
    for_family_member: Optional[str] = None
    confirmed: bool = False
    language: str = "en"


class AppointmentReschedule(BaseModel):
    date: str
    time: str


class RecordUploadMeta(BaseModel):
    patient_name: Optional[str] = None
    patient_phone: Optional[str] = None
    doctor_name: Optional[str] = None
    date: Optional[str] = None
    kind: str = "other"
    notes: Optional[str] = None


class ReminderCreate(BaseModel):
    record_id: Optional[str] = None
    appointment_token: Optional[str] = None
    type: str = "prescription_refill"   # prescription_refill | follow_up
    due_date: str                        # YYYY-MM-DD
    note: Optional[str] = None
    language: str = "en"
