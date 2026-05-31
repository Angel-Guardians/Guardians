"""Unit tests for admin table browser API."""
from __future__ import annotations

from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from backend.db.models import Location, Patient
from backend.db.session import get_session
from backend.main import create_app


@pytest.fixture
def api_client(db_session: Session) -> TestClient:
    app = create_app()

    def override_get_session():
        yield db_session

    app.dependency_overrides[get_session] = override_get_session
    return TestClient(app)


def test_list_admin_tables(api_client: TestClient, eleanor: Patient) -> None:
    res = api_client.get("/admin/tables")
    assert res.status_code == 200
    body = res.json()
    assert "tables" in body
    names = [t["name"] for t in body["tables"]]
    assert "patient" in names
    assert "emergencycontact" in names
    assert "location" in names
    patient_table = next(t for t in body["tables"] if t["name"] == "patient")
    assert patient_table["count"] == 1
    assert patient_table["rows"][0]["name"] == "Eleanor"
    assert patient_table["clearable"] is False
    location_table = next(t for t in body["tables"] if t["name"] == "location")
    assert location_table["clearable"] is True


def test_clear_location_table(api_client: TestClient, eleanor: Patient, db_session: Session) -> None:
    db_session.add(
        Location(
            patient_id=eleanor.id,
            ts=datetime.utcnow(),
            lat=43.65,
            lng=-79.38,
            accuracy=12.0,
            source="test",
        )
    )
    db_session.commit()

    res = api_client.delete("/admin/tables/location")
    assert res.status_code == 200
    body = res.json()
    assert body["table"] == "location"
    assert body["deleted"] == 1

    list_res = api_client.get("/admin/tables")
    location_table = next(t for t in list_res.json()["tables"] if t["name"] == "location")
    assert location_table["count"] == 0


def test_clear_patient_table_rejected(api_client: TestClient, eleanor: Patient) -> None:
    res = api_client.delete("/admin/tables/patient")
    assert res.status_code == 404
