"""Ingest, store and read lab-result records.

A lab record has two parts the brief calls out explicitly:

  * the **doc** - the original results document (PDF), saved to disk under
    ``settings.lab_documents_dir`` with its metadata kept in the ``LabReport``
    row; and
  * the **related rows** - one ``LabObservation`` per analyte parsed out of the
    document.

The document is always saved first, so a parse failure never loses the source
file - the report is just marked ``raw_only`` / ``needs_review`` for later
follow-up. Ingestion is idempotent per patient: identical files (same SHA-256)
are detected and not re-imported.
"""
from __future__ import annotations

import hashlib
from collections import Counter
from pathlib import Path

from loguru import logger
from sqlmodel import Session, select

from backend.api.schemas import (
    LabObservationRead,
    LabReportDetail,
    LabReportRead,
    LabUploadResult,
)
from backend.config import settings
from backend.db.models import LabObservation, LabReport
from backend.tools.integrations.lifelabs_pdf import (
    ParsedLabReport,
    PdfParseError,
    parse_lab_pdf,
)


class LabReportNotFoundError(LookupError):
    """Raised when a report id does not exist."""


def _documents_root() -> Path:
    return Path(settings.lab_documents_dir)


def store_document(patient_id: int, sha256: str, filename: str, data: bytes) -> str:
    """Persist the raw document and return its path relative to the data root."""
    suffix = Path(filename).suffix.lower() or ".pdf"
    rel_path = Path(str(patient_id)) / f"{sha256}{suffix}"
    abs_path = _documents_root() / rel_path
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    abs_path.write_bytes(data)
    return rel_path.as_posix()


def ingest_lab_pdf(
    session: Session,
    *,
    patient_id: int,
    filename: str,
    content_type: str,
    data: bytes,
    source: str = "lifelabs_upload",
    external_id: str | None = None,
) -> LabUploadResult:
    """Store a results PDF and its parsed observations. Idempotent per patient."""
    sha256 = hashlib.sha256(data).hexdigest()

    existing = session.exec(
        select(LabReport)
        .where(LabReport.patient_id == patient_id)
        .where(LabReport.document_sha256 == sha256)
    ).first()
    if existing is not None and existing.id is not None:
        count = _observation_count(session, existing.id)
        return LabUploadResult(
            report_id=existing.id,
            observations=count,
            duplicate=True,
            status=existing.status,
        )

    # Save the document first so the source is never lost, even if parsing fails.
    document_path = store_document(patient_id, sha256, filename, data)

    parsed: ParsedLabReport | None = None
    try:
        parsed = parse_lab_pdf(data)
    except PdfParseError as exc:
        logger.warning("lab PDF parse failed (patient={}): {}", patient_id, exc)

    if parsed is None:
        status = "raw_only"
    elif parsed.observations:
        status = "parsed"
    else:
        status = "needs_review"

    report = LabReport(
        patient_id=patient_id,
        source=source,
        external_id=external_id,
        lab_name=(parsed.lab_name if parsed else None),
        ordering_provider=(parsed.ordering_provider if parsed else None),
        collected_at=(parsed.collected_at if parsed else None),
        reported_at=(parsed.reported_at if parsed else None),
        document_path=document_path,
        document_filename=filename,
        document_sha256=sha256,
        content_type=content_type,
        raw_text=(parsed.raw_text if parsed else None),
        status=status,
    )
    session.add(report)
    session.flush()  # assign report.id
    assert report.id is not None

    if parsed is not None:
        for obs in parsed.observations:
            session.add(
                LabObservation(
                    report_id=report.id,
                    patient_id=patient_id,
                    test_name=obs.test_name,
                    value_text=obs.value_text,
                    value_num=obs.value_num,
                    unit=obs.unit,
                    reference_range=obs.reference_range,
                    flag=obs.flag,
                    category=obs.category,
                    observed_at=(parsed.collected_at or parsed.reported_at),
                )
            )

    session.commit()
    session.refresh(report)
    return LabUploadResult(
        report_id=report.id,
        observations=(len(parsed.observations) if parsed else 0),
        duplicate=False,
        status=status,
    )


def _observation_count(session: Session, report_id: int) -> int:
    return len(
        session.exec(
            select(LabObservation.id).where(LabObservation.report_id == report_id)
        ).all()
    )


def list_reports(session: Session, patient_id: int) -> list[LabReportRead]:
    reports = list(
        session.exec(
            select(LabReport)
            .where(LabReport.patient_id == patient_id)
            .order_by(LabReport.created_at.desc())  # type: ignore[union-attr]
        ).all()
    )
    if not reports:
        return []

    report_ids = [r.id for r in reports if r.id is not None]
    counts = Counter(
        session.exec(
            select(LabObservation.report_id).where(
                LabObservation.report_id.in_(report_ids)  # type: ignore[attr-defined]
            )
        ).all()
    )
    return [_to_report_read(r, counts.get(r.id, 0)) for r in reports]


def get_report_detail(session: Session, report_id: int) -> LabReportDetail:
    report = session.get(LabReport, report_id)
    if report is None or report.id is None:
        raise LabReportNotFoundError(report_id)

    observations = list(
        session.exec(
            select(LabObservation)
            .where(LabObservation.report_id == report_id)
            .order_by(LabObservation.id)  # type: ignore[arg-type]
        ).all()
    )
    base = _to_report_read(report, len(observations))
    return LabReportDetail(
        **base.model_dump(),
        raw_text=report.raw_text,
        observations=[
            LabObservationRead.model_validate(o, from_attributes=True)
            for o in observations
        ],
    )


def get_document(session: Session, report_id: int) -> tuple[Path, str, str]:
    """Return (absolute_path, download_filename, content_type) for the source doc."""
    report = session.get(LabReport, report_id)
    if report is None:
        raise LabReportNotFoundError(report_id)
    if not report.document_path:
        raise LabReportNotFoundError(report_id)
    abs_path = _documents_root() / report.document_path
    if not abs_path.exists():
        raise LabReportNotFoundError(report_id)
    return (
        abs_path,
        report.document_filename or f"report-{report_id}.pdf",
        report.content_type or "application/pdf",
    )


def _to_report_read(report: LabReport, observation_count: int) -> LabReportRead:
    assert report.id is not None
    return LabReportRead(
        id=report.id,
        patient_id=report.patient_id,
        source=report.source,
        lab_name=report.lab_name,
        ordering_provider=report.ordering_provider,
        collected_at=report.collected_at,
        reported_at=report.reported_at,
        document_filename=report.document_filename,
        status=report.status,
        created_at=report.created_at,
        observation_count=observation_count,
    )
