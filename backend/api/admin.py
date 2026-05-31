"""Dev admin routes — database table browser + selective row clearing."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session, SQLModel, func, select

from backend.db.models import (
    ConsentMatrix,
    EmergencyContact,
    EventLogEntry,
    Incident,
    LabObservation,
    LabReport,
    Location,
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
    Location,
    ReminderIntake,
    LabReport,
    LabObservation,
]

# Profile/seed tables are browse-only; the rest can be cleared from Admin.
_CLEARABLE_MODELS: dict[str, type[SQLModel]] = {
    model.__tablename__: model  # type: ignore[attr-defined]
    for model in (
        EventLogEntry,
        Incident,
        Vital,
        Location,
        ReminderIntake,
        LabObservation,
        LabReport,
    )
}

# Child rows must be removed before parent deletes succeed.
_CLEAR_DEPENDENTS: dict[str, list[str]] = {
    "labreport": ["labobservation"],
}


class AdminTableRead(BaseModel):
    name: str
    count: int
    rows: list[dict[str, Any]]
    clearable: bool = False


class AdminTablesRead(BaseModel):
    tables: list[AdminTableRead]


class AdminClearResult(BaseModel):
    table: str
    deleted: int


def _serialize_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    return value


def _serialize_row(row: SQLModel) -> dict[str, Any]:
    return {key: _serialize_value(val) for key, val in row.model_dump().items()}


def _delete_all(session: Session, model: type[SQLModel]) -> int:
    rows = list(session.exec(select(model)).all())
    for row in rows:
        session.delete(row)
    return len(rows)


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
                clearable=name in _CLEARABLE_MODELS,
            )
        )
    return AdminTablesRead(tables=tables)


@router.delete("/tables/{table_name}", response_model=AdminClearResult)
def clear_table(
    table_name: str,
    session: Session = Depends(get_session),
) -> AdminClearResult:
    """Delete all rows from a clearable table (dev / QA reset)."""
    name = table_name.strip().lower()
    model = _CLEARABLE_MODELS.get(name)
    if model is None:
        raise HTTPException(
            status_code=404,
            detail=f"Table '{table_name}' is not clearable.",
        )

    deleted = 0
    for dependent in _CLEAR_DEPENDENTS.get(name, []):
        dep_model = _CLEARABLE_MODELS.get(dependent)
        if dep_model is not None:
            deleted += _delete_all(session, dep_model)
    deleted += _delete_all(session, model)
    session.commit()
    return AdminClearResult(table=name, deleted=deleted)
