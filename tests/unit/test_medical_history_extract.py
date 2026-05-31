"""Tests for LLM-based medical-history extraction and profile merge.

The LLM call is stubbed with a fake client so these run with no network/model.
Two properties matter most and are asserted explicitly:

  * no hallucination — non-JSON / empty model output yields an empty extraction,
    never invented fields; and
  * no data loss — merging is additive (scalars fill only when empty, lists union
    case-insensitively, known medications are not duplicated).
"""
from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from backend.db.models import Medication, Patient
from backend.llm.base import LLMError, LLMResponse
from backend.services import medical_history_extract as mhx
from backend.services.medical_history_extract import (
    ExtractedProfile,
    apply_extraction_to_profile,
    extract_profile_from_text,
)


@pytest.fixture
def sqlite_session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    try:
        with Session(engine) as session:
            yield session
    finally:
        engine.dispose()


class _FakeLLM:
    """Returns a fixed text body for chat(), ignoring the prompt."""

    def __init__(self, text: str) -> None:
        self._text = text
        self.capabilities = None

    def chat(self, messages, tools=None, **kw):  # noqa: ANN001
        return LLMResponse(text=self._text)


# ---------------------------------------------------------------------------
# Extraction (LLM stubbed)
# ---------------------------------------------------------------------------


def test_extract_parses_well_formed_json():
    llm = _FakeLLM(
        '{"name":"Eleanor Vance","age":78,"conditions":["Type 2 Diabetes"],'
        '"allergies":["Penicillin"],'
        '"medications":[{"name":"Metformin","dose":"500 mg","notes":"BID"}],'
        '"notes":"Lives alone."}'
    )
    p = extract_profile_from_text("some document text", llm=llm)
    assert p.name == "Eleanor Vance"
    assert p.age == 78
    assert p.conditions == ["Type 2 Diabetes"]
    assert p.allergies == ["Penicillin"]
    assert p.medications[0].name == "Metformin"
    assert p.medications[0].dose == "500 mg"


def test_extract_tolerates_markdown_fences_and_prose():
    llm = _FakeLLM(
        'Sure, here is the data:\n```json\n{"name":"Bob","conditions":["Asthma"]}\n```'
    )
    p = extract_profile_from_text("doc", llm=llm)
    assert p.name == "Bob"
    assert p.conditions == ["Asthma"]


def test_extract_does_not_hallucinate_on_non_json():
    # Model says it found nothing structured -> empty extraction, not invented data.
    p = extract_profile_from_text("doc", llm=_FakeLLM("I could not find any fields."))
    assert p == ExtractedProfile()


def test_extract_empty_text_skips_llm():
    # Empty document should not even call the model.
    p = extract_profile_from_text("   ", llm=_FakeLLM("should not be used"))
    assert p == ExtractedProfile()


def test_extract_and_apply_handles_llm_error(sqlite_session, monkeypatch):
    sqlite_session.add(Patient(id=1, name="X", age=1))
    sqlite_session.commit()

    def _boom(*a, **k):
        raise LLMError("no endpoint")

    monkeypatch.setattr(mhx, "extract_profile_from_text", _boom)
    summary = mhx.extract_and_apply_profile(sqlite_session, patient_id=1, raw_text="text")
    assert summary.applied is False
    assert summary.error == "LLM extraction failed"


# ---------------------------------------------------------------------------
# Merge (additive, non-destructive)
# ---------------------------------------------------------------------------


def test_apply_is_additive_and_non_destructive(sqlite_session):
    # Existing curated profile: name set, age set, one condition already present.
    sqlite_session.add(
        Patient(
            id=1,
            name="Eleanor V",
            age=82,
            conditions=["Hypertension"],
            allergies=[],
        )
    )
    sqlite_session.commit()

    extracted = ExtractedProfile(
        name="Eleanor Vance",  # should NOT overwrite existing name
        age=78,  # should NOT overwrite existing age
        conditions=["hypertension", "Type 2 Diabetes"],  # dup (case) + new
        allergies=["Penicillin"],
        medications=[mhx.ExtractedMedicationModel(name="Metformin", dose="500 mg")],
        notes="Lives alone.",
    )
    summary = apply_extraction_to_profile(sqlite_session, 1, extracted)

    patient = sqlite_session.get(Patient, 1)
    assert patient.name == "Eleanor V"  # preserved
    assert patient.age == 82  # preserved
    assert patient.conditions == ["Hypertension", "Type 2 Diabetes"]  # union, no dup
    assert patient.allergies == ["Penicillin"]
    assert patient.notes == "Lives alone."

    meds = sqlite_session.exec(select(Medication)).all()
    assert [m.name for m in meds] == ["Metformin"]
    assert meds[0].schedule_cron == ""  # not fabricated

    # Summary reflects only what actually changed.
    assert summary.name is None  # name not changed
    assert summary.age is None  # age not changed
    assert summary.conditions_added == ["Type 2 Diabetes"]
    assert summary.allergies_added == ["Penicillin"]
    assert summary.medications_added == ["Metformin"]
    assert summary.notes_added is True


def test_apply_fills_empty_scalars(sqlite_session):
    sqlite_session.add(Patient(id=1, name="", age=0, conditions=[], allergies=[]))
    sqlite_session.commit()

    extracted = ExtractedProfile(name="Jane Doe", age=65)
    summary = apply_extraction_to_profile(sqlite_session, 1, extracted)

    patient = sqlite_session.get(Patient, 1)
    assert patient.name == "Jane Doe"
    assert patient.age == 65
    assert summary.name == "Jane Doe"
    assert summary.age == 65


def test_apply_skips_duplicate_medication(sqlite_session):
    sqlite_session.add(Patient(id=1, name="A", age=50, conditions=[], allergies=[]))
    sqlite_session.add(Medication(patient_id=1, name="Metformin", dose="500 mg", schedule_cron="0 8 * * *"))
    sqlite_session.commit()

    extracted = ExtractedProfile(
        medications=[mhx.ExtractedMedicationModel(name="metformin", dose="850 mg")]
    )
    summary = apply_extraction_to_profile(sqlite_session, 1, extracted)

    meds = sqlite_session.exec(select(Medication)).all()
    assert len(meds) == 1  # not duplicated
    assert summary.medications_added == []
