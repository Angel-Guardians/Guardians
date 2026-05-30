"""Unit tests for admin table browser API."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from backend.db.models import Patient
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
    patient_table = next(t for t in body["tables"] if t["name"] == "patient")
    assert patient_table["count"] == 1
    assert patient_table["rows"][0]["name"] == "Eleanor"
