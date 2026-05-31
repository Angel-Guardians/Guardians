"""Tests for lab-record parsing, ingestion and the HTTP upload path.

These are deliberately self-contained: the PDF parser's row mapping is a pure
function (tested directly, no real PDF), and the service / HTTP tests run on an
in-memory SQLite engine with a temp documents dir - so neither pdfplumber's
table detection, Docker/Postgres, nor any network is required to run them.
"""
from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from backend.config import settings
from backend.db.models import LabObservation, LabReport, Patient
from backend.services import lab_records
from backend.tools.integrations.lifelabs_pdf import (
    ParsedLabReport,
    ParsedObservation,
    metadata_from_text,
    observations_from_tables,
)


@pytest.fixture
def sqlite_session() -> Iterator[Session]:
    """In-memory SQLite session with the full schema (no Docker needed)."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    try:
        with Session(engine) as session:
            yield session
    finally:
        engine.dispose()


# ---------------------------------------------------------------------------
# Parser (pure)
# ---------------------------------------------------------------------------


def test_observations_from_tables_maps_columns_and_sections():
    tables = [
        [
            ["Hematology"],
            ["Test", "Result", "Flag", "Reference Range", "Units"],
            ["Hemoglobin", "118", "L", "120 - 160", "g/L"],
            ["WBC", "6.2", "", "4.0 - 11.0", "x10E9/L"],
        ]
    ]
    obs = observations_from_tables(tables)
    assert len(obs) == 2

    hgb = obs[0]
    assert hgb.test_name == "Hemoglobin"
    assert hgb.value_text == "118"
    assert hgb.value_num == 118.0
    assert hgb.unit == "g/L"
    assert hgb.reference_range == "120 - 160"
    assert hgb.flag == "L"
    assert hgb.category == "Hematology"

    assert obs[1].flag is None  # empty flag cell -> normal


def test_observations_positional_fallback_without_header():
    tables = [[["Glucose, Fasting", "5.4", "mmol/L", "3.6 - 6.0"]]]
    obs = observations_from_tables(tables)
    assert len(obs) == 1
    assert obs[0].test_name == "Glucose, Fasting"
    assert obs[0].value_num == 5.4
    assert obs[0].unit == "mmol/L"


def test_observations_parses_flag_embedded_in_result():
    tables = [
        [
            ["Test", "Result", "Reference Range"],
            ["Potassium", "5.6 (H)", "3.5 - 5.1"],
        ]
    ]
    obs = observations_from_tables(tables)
    assert obs[0].value_text == "5.6"
    assert obs[0].value_num == 5.6
    assert obs[0].flag == "H"


def test_metadata_from_text_extracts_dates_and_provider():
    text = "Collection Date: 2026-05-20\nReported: 2026-05-22\nOrdering Physician: Dr. Jane Smith"
    meta = metadata_from_text(text)
    assert meta["collected_at"] == datetime(2026, 5, 20)
    assert meta["reported_at"] == datetime(2026, 5, 22)
    assert "Jane Smith" in str(meta["ordering_provider"])


# ---------------------------------------------------------------------------
# Service ingest (stubbed parser + temp storage)
# ---------------------------------------------------------------------------


def test_ingest_stores_document_and_rows(sqlite_session, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "lab_documents_dir", str(tmp_path))
    sqlite_session.add(Patient(id=1, name="Eleanor Vance", age=82))
    sqlite_session.commit()

    def fake_parse(_data: bytes) -> ParsedLabReport:
        return ParsedLabReport(
            raw_text="Hemoglobin 118 g/L",
            observations=[
                ParsedObservation(
                    test_name="Hemoglobin", value_text="118", value_num=118.0,
                    unit="g/L", flag="L", category="Hematology",
                ),
            ],
            collected_at=datetime(2026, 5, 20),
        )

    monkeypatch.setattr(lab_records, "parse_lab_pdf", fake_parse)

    result = lab_records.ingest_lab_pdf(
        sqlite_session, patient_id=1, filename="results.pdf",
        content_type="application/pdf", data=b"%PDF-1.4 fake bytes",
    )

    assert result.duplicate is False
    assert result.observations == 1
    assert result.status == "parsed"

    report = sqlite_session.get(LabReport, result.report_id)
    assert report is not None and report.document_sha256
    assert (tmp_path / report.document_path).exists()  # doc written to disk

    rows = sqlite_session.exec(
        select(LabObservation).where(LabObservation.report_id == result.report_id)
    ).all()
    assert len(rows) == 1 and rows[0].test_name == "Hemoglobin"


def test_ingest_is_idempotent_on_identical_file(sqlite_session, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "lab_documents_dir", str(tmp_path))
    sqlite_session.add(Patient(id=1, name="Eleanor Vance", age=82))
    sqlite_session.commit()
    monkeypatch.setattr(
        lab_records, "parse_lab_pdf",
        lambda _d: ParsedLabReport(raw_text="x", observations=[]),
    )

    data = b"%PDF-1.4 identical"
    first = lab_records.ingest_lab_pdf(
        sqlite_session, patient_id=1, filename="a.pdf",
        content_type="application/pdf", data=data,
    )
    second = lab_records.ingest_lab_pdf(
        sqlite_session, patient_id=1, filename="a.pdf",
        content_type="application/pdf", data=data,
    )

    assert first.duplicate is False
    assert second.duplicate is True
    assert second.report_id == first.report_id
    assert first.status == "needs_review"  # no observations parsed
    assert len(sqlite_session.exec(select(LabReport)).all()) == 1


# ---------------------------------------------------------------------------
# HTTP end-to-end (real multipart + storage round-trip, SQLite-backed)
#
# The parser is stubbed so the test is deterministic and focuses on what is
# *our* code: multipart upload, dedup, persistence, list/detail, and a
# byte-exact document download round-trip. pdfplumber's own text/table
# extraction is exercised by the pure parser tests above.
# ---------------------------------------------------------------------------


def test_upload_endpoint_end_to_end(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "lab_documents_dir", str(tmp_path / "docs"))
    monkeypatch.setattr(
        lab_records,
        "parse_lab_pdf",
        lambda _d: ParsedLabReport(
            raw_text="Hemoglobin 118 g/L",
            observations=[ParsedObservation(test_name="Hemoglobin", value_text="118")],
            collected_at=datetime(2026, 5, 20),
        ),
    )

    # The upload path also runs an LLM profile-extraction pass. Stub it so the
    # test stays hermetic (no network / model) and deterministic. The dedicated
    # extraction logic is unit-tested separately in test_medical_history_extract.
    from backend.api.schemas import MedicalHistoryExtraction

    monkeypatch.setattr(
        lab_records,
        "extract_and_apply_profile",
        lambda *a, **k: MedicalHistoryExtraction(
            applied=True, conditions_added=["Anemia"]
        ),
    )

    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)

    def _session_override() -> Iterator[Session]:
        with Session(engine) as session:
            yield session

    from backend.db.session import get_session
    from backend.main import app

    app.dependency_overrides[get_session] = _session_override
    try:
        with Session(engine) as s:
            s.add(Patient(id=1, name="Eleanor", age=70))
            s.commit()

        client = TestClient(app)
        pdf_bytes = b"%PDF-1.4 lab results payload \n123"

        resp = client.post(
            "/lab-records/upload",
            files={"file": ("results.pdf", pdf_bytes, "application/pdf")},
            data={"patient_id": "1"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        report_id = body["report_id"]
        assert body["observations"] == 1
        assert body["status"] == "parsed"
        assert body["duplicate"] is False
        # LLM-extracted profile fields are surfaced on the upload result.
        assert body["profile"]["applied"] is True
        assert body["profile"]["conditions_added"] == ["Anemia"]

        # Re-upload identical bytes -> deduped, same report.
        again = client.post(
            "/lab-records/upload",
            files={"file": ("results.pdf", pdf_bytes, "application/pdf")},
            data={"patient_id": "1"},
        )
        assert again.json()["duplicate"] is True
        assert again.json()["report_id"] == report_id

        listed = client.get("/lab-records", params={"patient_id": 1})
        assert listed.status_code == 200
        assert [r["id"] for r in listed.json()] == [report_id]  # no duplicate row

        detail = client.get(f"/lab-records/{report_id}")
        assert detail.status_code == 200
        assert detail.json()["raw_text"] == "Hemoglobin 118 g/L"
        assert detail.json()["observations"][0]["test_name"] == "Hemoglobin"

        # Document download returns the exact bytes we uploaded.
        doc = client.get(f"/lab-records/{report_id}/document")
        assert doc.status_code == 200
        assert doc.content == pdf_bytes

        # Non-PDF is rejected; unknown report 404s.
        bad = client.post(
            "/lab-records/upload",
            files={"file": ("notes.txt", b"hello", "text/plain")},
            data={"patient_id": "1"},
        )
        assert bad.status_code == 415
        assert client.get("/lab-records/99999").status_code == 404
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_lifelabs_fetch_returns_501_scaffold():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)

    def _session_override() -> Iterator[Session]:
        with Session(engine) as session:
            yield session

    from backend.db.session import get_session
    from backend.main import app

    app.dependency_overrides[get_session] = _session_override
    try:
        client = TestClient(app)
        resp = client.post("/lab-records/lifelabs/fetch", params={"patient_id": 1})
        assert resp.status_code == 501
        assert "not implemented" in resp.json()["detail"].lower()
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
