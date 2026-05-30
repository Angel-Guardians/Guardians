"""Request/response schemas for the HTTP API."""
from __future__ import annotations

from pydantic import BaseModel, Field


class EmergencyContactRead(BaseModel):
    id: int
    name: str
    relationship: str
    phone: str
    priority: int


class EmergencyContactWrite(BaseModel):
    name: str
    relationship: str
    phone: str
    priority: int = 1


class ProfileMedicationRead(BaseModel):
    id: int
    name: str
    dose: str
    schedule_cron: str
    with_food: bool
    notes: str | None = None


class ProfileMedicationWrite(BaseModel):
    name: str
    dose: str
    schedule_cron: str
    with_food: bool = False
    notes: str | None = None


class PatientProfileRead(BaseModel):
    id: int
    name: str
    age: int
    conditions: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    primary_language: str = "en"
    notes: str | None = None
    emergency_contacts: list[EmergencyContactRead] = Field(default_factory=list)
    medications: list[ProfileMedicationRead] = Field(default_factory=list)


class PatientProfileWrite(BaseModel):
    name: str
    age: int
    conditions: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    primary_language: str = "en"
    notes: str | None = None
    emergency_contacts: list[EmergencyContactWrite] = Field(default_factory=list)
    medications: list[ProfileMedicationWrite] = Field(default_factory=list)
