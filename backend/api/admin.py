"""Dev admin routes — read-only database table browser."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlmodel import Session, SQLModel, func, select

from backend.db.models import (
    ConsentMatrix,
    EmergencyContact,
    EventLogEntry,
    Incident,
    LabObservation,
    LabReport,
    Medication,
    Patient,
    ReminderIntake,
    Vital,
)
from backend.db.session import get_session

router = APIRouter()

TABLE_MODELS: list[type[SQLModel]] = [
    Patient,
    EmergencyContact,
    Medication,
    ConsentMatrix,
    EventLogEntry,
    Incident,
    Vital,
    ReminderIntake,
    LabReport,
    LabObservation,
]


class AdminTableRead(BaseModel):
    name: str
    count: int
    rows: list[dict[str, Any]]


class AdminTablesRead(BaseModel):
    tables: list[AdminTableRead]


def _serialize_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    return value


def _serialize_row(row: SQLModel) -> dict[str, Any]:
    return {key: _serialize_value(val) for key, val in row.model_dump().items()}


@router.get("/tables", response_model=AdminTablesRead)
def list_tables(
    session: Session = Depends(get_session),
    limit: int = Query(default=50, ge=1, le=500),
) -> AdminTablesRead:
    tables: list[AdminTableRead] = []
    for model in TABLE_MODELS:
        assert hasattr(model, "__tablename__")
        name = model.__tablename__  # type: ignore[attr-defined]
        rows = list(session.exec(select(model).limit(limit)).all())
        count = session.exec(select(func.count()).select_from(model)).one()
        tables.append(
            AdminTableRead(
                name=name,
                count=count,
                rows=[_serialize_row(row) for row in rows],
            )
        )
    return AdminTablesRead(tables=tables)
