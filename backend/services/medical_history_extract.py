"""Extract structured patient-profile fields from a medical document via the LLM.

The lab-PDF parser (``lifelabs_pdf``) only understands tabular lab results. A
free-form *medical history* document — demographics, problem list, allergies,
current medications — is prose, so we hand its extracted text to the LLM and ask
for the specific fields our ``Patient`` profile stores.

Flow:
    raw_text  ->  LLM (strict, no-hallucination prompt)  ->  ExtractedProfile
              ->  merged *additively* into the Patient profile.

Two hard rules drive the design:

* **No hallucination.** The prompt forbids guessing; a field is emitted only when
  the document states it. The model returns JSON we validate against
  :class:`ExtractedProfile` (unknown/garbled output degrades to "extracted
  nothing", never to fabricated data).
* **No data loss.** Merging is additive — scalar fields (name, age) are filled
  only when the profile's value is empty, and list fields (conditions, allergies,
  medications) are unioned case-insensitively. An upload can enrich a profile but
  never clobbers a curated one.
"""
from __future__ import annotations

import json
import re

from loguru import logger
from pydantic import BaseModel, Field, ValidationError
from sqlmodel import Session, select

from backend.api.schemas import MedicalHistoryExtraction
from backend.db.models import Medication, Patient
from backend.llm import LLMClient, Message, build_llm
from backend.llm.base import LLMError

# Medical-history docs are short; cap the prompt so a stray huge PDF can't blow up
# the context window or the request cost.
_MAX_CHARS = 12000


class ExtractedMedicationModel(BaseModel):
    name: str
    dose: str | None = None
    notes: str | None = None


class ExtractedProfile(BaseModel):
    """The shape we ask the LLM to return — every field optional, defaults empty."""

    name: str | None = None
    age: int | None = None
    conditions: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    medications: list[ExtractedMedicationModel] = Field(default_factory=list)
    notes: str | None = None


_SYSTEM_PROMPT = """You are a clinical data-extraction assistant. You read a single \
medical document and extract ONLY the patient information that is explicitly present \
in the text. You must NOT guess, infer, normalise, or invent anything.

Return a single JSON object with exactly this shape:
{
  "name": string | null,        // patient's full name, only if stated
  "age": integer | null,        // age in years, only if stated as a number
  "conditions": string[],       // diagnoses / chronic conditions / problem list
  "allergies": string[],        // drug or food allergies
  "medications": [              // current medications
    { "name": string, "dose": string | null, "notes": string | null }
  ],
  "notes": string | null        // other clinically relevant detail, kept brief
}

Rules:
- Include a value ONLY if the document explicitly supports it. If something is not
  stated, use null (for scalars) or an empty array (for lists). Never fabricate.
- Do not translate, expand, or convert units/values beyond what is written.
- Keep condition and allergy names concise (e.g. "Type 2 Diabetes", "Penicillin").
- If the document is not about a patient or contains none of these fields, return
  every field empty/null.
- Output JSON only. No prose, no explanation, no markdown code fences."""


# ---------------------------------------------------------------------------
# LLM extraction
# ---------------------------------------------------------------------------


def extract_profile_from_text(
    raw_text: str | None, llm: LLMClient | None = None
) -> ExtractedProfile:
    """Ask the LLM to pull profile fields out of ``raw_text``. Pure of DB I/O."""
    text = (raw_text or "").strip()
    if not text:
        return ExtractedProfile()

    llm = llm or build_llm()
    response = llm.chat(
        [
            Message(role="system", content=_SYSTEM_PROMPT),
            Message(role="user", content=f"MEDICAL DOCUMENT:\n\n{text[:_MAX_CHARS]}"),
        ],
        temperature=0,  # deterministic extraction; discourages embellishment
    )
    return _parse_extraction(response.text)


def _parse_extraction(text: str | None) -> ExtractedProfile:
    obj = _extract_json_object(text)
    if obj is None:
        logger.warning("medical-history extraction: no JSON object in LLM output")
        return ExtractedProfile()
    try:
        return ExtractedProfile.model_validate(obj)
    except ValidationError as exc:
        logger.warning("medical-history extraction: invalid shape: {}", exc)
        return ExtractedProfile()


_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


def _extract_json_object(text: str | None) -> dict | None:
    """Tolerant JSON extraction — strips markdown fences and stray prose."""
    if not text:
        return None
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned).strip()
    try:
        parsed = json.loads(cleaned)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        pass
    match = _JSON_RE.search(cleaned)
    if not match:
        return None
    try:
        parsed = json.loads(match.group(0))
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        return None


# ---------------------------------------------------------------------------
# Merge into the patient profile (additive, never destructive)
# ---------------------------------------------------------------------------


def _norm(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().lower()


def apply_extraction_to_profile(
    session: Session, patient_id: int, extracted: ExtractedProfile
) -> MedicalHistoryExtraction:
    """Merge extracted fields into the patient profile and report what changed."""
    patient = session.get(Patient, patient_id)
    if patient is None:
        return MedicalHistoryExtraction(applied=False, error="patient not found")

    summary = MedicalHistoryExtraction(applied=True)

    # Scalars: fill only when currently empty, so we never overwrite a curated value.
    if extracted.name and not (patient.name or "").strip():
        patient.name = extracted.name.strip()
        summary.name = patient.name
    if extracted.age and not patient.age:
        patient.age = extracted.age
        summary.age = patient.age

    # Lists: union case-insensitively. Reassign (don't mutate in place) so SQLModel
    # marks the JSON column dirty.
    seen_conditions = {_norm(c) for c in patient.conditions}
    for raw in extracted.conditions:
        cond = raw.strip()
        if cond and _norm(cond) not in seen_conditions:
            patient.conditions = patient.conditions + [cond]
            seen_conditions.add(_norm(cond))
            summary.conditions_added.append(cond)

    seen_allergies = {_norm(a) for a in patient.allergies}
    for raw in extracted.allergies:
        allergy = raw.strip()
        if allergy and _norm(allergy) not in seen_allergies:
            patient.allergies = patient.allergies + [allergy]
            seen_allergies.add(_norm(allergy))
            summary.allergies_added.append(allergy)

    # Medications: add by name (case-insensitive) if not already on file. We do NOT
    # invent a schedule — a history doc rarely states a cron — so schedule_cron is
    # left empty and any frequency text the model captured stays in notes.
    existing_meds = {
        _norm(m.name)
        for m in session.exec(
            select(Medication).where(Medication.patient_id == patient_id)
        ).all()
    }
    for med in extracted.medications:
        name = (med.name or "").strip()
        if not name or _norm(name) in existing_meds:
            continue
        session.add(
            Medication(
                patient_id=patient_id,
                name=name,
                dose=(med.dose or "").strip(),
                schedule_cron="",
                with_food=False,
                notes=(med.notes.strip() if med.notes else None),
            )
        )
        existing_meds.add(_norm(name))
        summary.medications_added.append(name)

    # Notes: append if present and not already captured.
    if extracted.notes and extracted.notes.strip():
        note = extracted.notes.strip()
        current = (patient.notes or "").strip()
        if note.lower() not in current.lower():
            patient.notes = f"{current}\n{note}".strip() if current else note
            summary.notes_added = True

    session.add(patient)
    session.commit()
    return summary


def extract_and_apply_profile(
    session: Session,
    *,
    patient_id: int,
    raw_text: str | None,
    llm: LLMClient | None = None,
) -> MedicalHistoryExtraction:
    """Full path used by the upload endpoint. Extraction failures are non-fatal:
    the document + lab rows are already stored; we just report the error."""
    if not (raw_text or "").strip():
        return MedicalHistoryExtraction(applied=False, error="no text to extract")
    try:
        extracted = extract_profile_from_text(raw_text, llm=llm)
    except LLMError as exc:
        logger.warning("medical-history LLM extraction failed (patient={}): {}", patient_id, exc)
        return MedicalHistoryExtraction(applied=False, error="LLM extraction failed")
    except Exception as exc:  # never let extraction break an otherwise-good upload
        logger.warning("medical-history extraction error (patient={}): {}", patient_id, exc)
        return MedicalHistoryExtraction(applied=False, error="extraction error")
    return apply_extraction_to_profile(session, patient_id, extracted)
