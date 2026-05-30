"""Unit tests for patient profile API."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from backend.api.schemas import PatientProfileWrite
from backend.db.models import Medication, Patient
from backend.db.session import get_session
from backend.main import create_app


@pytest.fixture
def api_client(db_session: Session) -> TestClient:
    app = create_app()

    def override_get_session():
        yield db_session

    app.dependency_overrides[get_session] = override_get_session
    return TestClient(app)


@pytest.fixture
def eleanor_profile(db_session: Session, eleanor: Patient) -> Patient:
    db_session.add_all(
        [
            Medication(
                patient_id=eleanor.id,
                name="Lisinopril",
                dose="10 mg",
                schedule_cron="0 8 * * *",
            ),
        ]
    )
    db_session.commit()
    return eleanor


def test_get_patient_profile(api_client: TestClient, eleanor_profile: Patient) -> None:
    res = api_client.get(f"/patient/{eleanor_profile.id}/profile")
    assert res.status_code == 200
    body = res.json()
    assert body["name"] == "Eleanor"
    assert body["age"] == 70
    assert "cardiac" in body["conditions"][0]
    assert len(body["emergency_contacts"]) == 2
    assert len(body["medications"]) == 1


def test_get_patient_profile_not_found(api_client: TestClient) -> None:
    res = api_client.get("/patient/999/profile")
    assert res.status_code == 404


def test_update_patient_profile(api_client: TestClient, eleanor_profile: Patient) -> None:
    patient_id = eleanor_profile.id
    assert patient_id is not None

    payload = {
        "name": "Eleanor",
        "age": 71,
        "conditions": ["cardiac history"],
        "allergies": ["penicillin", "shellfish"],
        "primary_language": "en",
        "notes": "Updated notes",
        "emergency_contacts": [
            {
                "name": "Maria",
                "relationship": "daughter",
                "phone": "+15555550111",
                "priority": 1,
            }
        ],
        "medications": [
            {
                "name": "Aspirin",
                "dose": "81 mg",
                "schedule_cron": "0 9 * * *",
                "with_food": True,
                "notes": None,
            }
        ],
    }

    res = api_client.put(f"/patient/{patient_id}/profile", json=payload)
    assert res.status_code == 200
    body = res.json()
    assert body["age"] == 71
    assert body["allergies"] == ["penicillin", "shellfish"]
    assert len(body["emergency_contacts"]) == 1
    assert body["emergency_contacts"][0]["name"] == "Maria"
    assert len(body["medications"]) == 1
    assert body["medications"][0]["name"] == "Aspirin"


def test_update_patient_profile_not_found(api_client: TestClient) -> None:
    payload = PatientProfileWrite(name="Nobody", age=40).model_dump()
    res = api_client.put("/patient/999/profile", json=payload)
    assert res.status_code == 404
