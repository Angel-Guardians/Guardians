"""Lab / health-record routes.

POST /lab-records/upload           - upload a results PDF; parse + store doc + rows.
GET  /lab-records                  - list a patient's reports (with row counts).
GET  /lab-records/{id}             - one report + its parsed observations.
GET  /lab-records/{id}/document    - download the original stored PDF.
POST /lab-records/lifelabs/fetch   - (scaffold) crawl MyCareCompass; 501 for now.

LifeLabs has no public patient API, so the upload path is primary; the fetch
endpoint is wired to the crawler scaffold and returns 501 until implemented.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlmodel import Session

from backend.api.schemas import LabReportDetail, LabReportRead, LabUploadResult
from backend.db.session import get_session
from backend.services.lab_records import (
    LabReportNotFoundError,
    get_document,
    get_report_detail,
    ingest_lab_pdf,
    list_reports,
)
from backend.tools.integrations.lifelabs_client import (
    LifeLabsClient,
    LifeLabsCrawlerNotImplemented,
)

router = APIRouter()

_MAX_BYTES = 25 * 1024 * 1024  # 25 MB - lab PDFs are small; guard against abuse.


@router.post("/upload", response_model=LabUploadResult)
def upload_lab_pdf(
    patient_id: int = Form(1),
    source: str = Form("lifelabs_upload"),
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
) -> LabUploadResult:
    """Accept a results PDF, parse it, and store the document + observation rows."""
    filename = file.filename or "upload.pdf"
    is_pdf = (file.content_type == "application/pdf") or filename.lower().endswith(".pdf")
    if not is_pdf:
        raise HTTPException(status_code=415, detail="expected a PDF file")

    data = file.file.read()
    if not data:
        raise HTTPException(status_code=400, detail="empty file")
    if len(data) > _MAX_BYTES:
        raise HTTPException(status_code=413, detail="file too large")

    return ingest_lab_pdf(
        session,
        patient_id=patient_id,
        filename=filename,
        content_type=file.content_type or "application/pdf",
        data=data,
        source=source,
    )


@router.get("", response_model=list[LabReportRead])
def list_lab_reports(
    patient_id: int = 1,
    session: Session = Depends(get_session),
) -> list[LabReportRead]:
    return list_reports(session, patient_id)


@router.get("/{report_id}", response_model=LabReportDetail)
def read_lab_report(
    report_id: int,
    session: Session = Depends(get_session),
) -> LabReportDetail:
    try:
        return get_report_detail(session, report_id)
    except LabReportNotFoundError:
        raise HTTPException(status_code=404, detail="lab report not found") from None


@router.get("/{report_id}/document")
def download_lab_document(
    report_id: int,
    session: Session = Depends(get_session),
) -> FileResponse:
    try:
        path, filename, content_type = get_document(session, report_id)
    except LabReportNotFoundError:
        raise HTTPException(status_code=404, detail="document not found") from None
    return FileResponse(path, media_type=content_type, filename=filename)


@router.post("/lifelabs/fetch", response_model=LabUploadResult)
async def fetch_from_lifelabs(
    patient_id: int = 1,
    session: Session = Depends(get_session),
) -> LabUploadResult:
    """Crawl MyCareCompass and ingest the patient's own results. Scaffold (501)."""
    client = LifeLabsClient()
    try:
        reports = await client.fetch_reports()
    except LifeLabsCrawlerNotImplemented as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from None

    # When the crawler is implemented, each remote report flows through the same
    # ingest path as uploads (dedup by SHA-256, parse, store doc + rows).
    last: LabUploadResult | None = None
    for remote in reports:
        last = ingest_lab_pdf(
            session,
            patient_id=patient_id,
            filename=remote.filename,
            content_type="application/pdf",
            data=remote.content,
            source="lifelabs_mycarecompass",
            external_id=remote.external_id,
        )
    if last is None:
        raise HTTPException(status_code=204, detail="no new reports")
    return last
