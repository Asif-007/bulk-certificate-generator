import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app


@pytest.fixture
def test_client(monkeypatch, tmp_path):
    """Create an isolated SQLite database and test client."""

    database_url = f"sqlite:///{(tmp_path / 'test.db').as_posix()}"

    test_engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False},
    )

    TestingSessionLocal = sessionmaker(
        bind=test_engine,
        autoflush=False,
        expire_on_commit=False,
    )

    Base.metadata.create_all(bind=test_engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    # Background job processing also needs to use the test database.
    monkeypatch.setattr("app.main.SessionLocal", TestingSessionLocal)
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


def valid_payload():
    return {
        "certificate": {
            "course_name": "Python Programming",
            "issuer": "ABC Institute",
            "completion_date": "2026-10-10",
        },
        "recipients": [
            {"name": "Asif", "email": "asif@example.com"},
            {"name": "Rahul", "email": "rahul@example.com"},
        ],
    }


def test_health_endpoint(test_client):
    response = test_client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_invalid_email_is_rejected(test_client):
    payload = valid_payload()
    payload["recipients"][0]["email"] = "not-an-email"

    response = test_client.post("/jobs", json=payload)

    assert response.status_code == 422


def test_empty_recipient_list_is_rejected(test_client):
    payload = valid_payload()
    payload["recipients"] = []

    response = test_client.post("/jobs", json=payload)

    assert response.status_code == 422


def test_create_job_processes_recipients_and_tracks_progress(
    test_client,
):
    response = test_client.post("/jobs", json=valid_payload())

    assert response.status_code == 202
    job_id = response.json()["job_id"]

    status_response = test_client.get(f"/jobs/{job_id}")

    assert status_response.status_code == 200
    job = status_response.json()

    assert job["job_id"] == job_id
    assert job["status"] == "completed"
    assert job["total_count"] == 2
    assert job["success_count"] == 2
    assert job["failed_count"] == 0
    assert job["processed_count"] == 2
    assert job["progress_percent"] == 100

    assert all(
        recipient["status"] == "succeeded"
        for recipient in job["recipients"]
    )

    assert all(
        recipient["certificate_url"]
        for recipient in job["recipients"]
    )


def test_successful_certificate_can_be_downloaded(test_client):
    response = test_client.post("/jobs", json=valid_payload())

    assert response.status_code == 202
    job_id = response.json()["job_id"]

    job_response = test_client.get(f"/jobs/{job_id}")
    assert job_response.status_code == 200

    recipient = job_response.json()["recipients"][0]
    recipient_id = recipient["recipient_id"]

    download_response = test_client.get(
        f"/jobs/{job_id}/recipients/{recipient_id}/certificate"
    )

    assert download_response.status_code == 200
    assert download_response.headers["content-type"] == "application/pdf"
    assert download_response.content.startswith(b"%PDF-")


def test_one_recipient_failure_does_not_stop_others(
    test_client, monkeypatch, tmp_path
):
    from app import main

    output_dir = tmp_path / "generated_certificates"
    output_dir.mkdir()
    monkeypatch.setattr(main, "OUTPUT_DIR", output_dir)

    def fake_generate_certificate(
        recipient_name, course_name, issuer, completion_date
    ):
        if recipient_name == "Asif":
            raise RuntimeError("Simulated PDF generation failure")

        file_path = output_dir / "rahul.pdf"
        file_path.write_bytes(b"%PDF-1.4\nfake test PDF\n%%EOF")
        return file_path

    monkeypatch.setattr(
        main, "generate_certificate", fake_generate_certificate
    )

    response = test_client.post("/jobs", json=valid_payload())
    assert response.status_code == 202

    job_id = response.json()["job_id"]
    job_response = test_client.get(f"/jobs/{job_id}")

    assert job_response.status_code == 200
    job = job_response.json()

    assert job["status"] == "partially_failed"
    assert job["total_count"] == 2
    assert job["success_count"] == 1
    assert job["failed_count"] == 1
    assert job["processed_count"] == 2
    assert job["progress_percent"] == 100

    recipients = {r["name"]: r for r in job["recipients"]}

    assert recipients["Asif"]["status"] == "failed"
    assert "Simulated PDF generation failure" in (
        recipients["Asif"]["error_message"]
    )

    assert recipients["Rahul"]["status"] == "succeeded"
    assert recipients["Rahul"]["certificate_url"] is not None


def test_nonexistent_job_returns_404(test_client):
    response = test_client.get("/jobs/999999")

    assert response.status_code == 404


def test_recipient_from_another_job_returns_404(test_client):
    first_response = test_client.post("/jobs", json=valid_payload())
    second_response = test_client.post("/jobs", json=valid_payload())

    assert first_response.status_code == 202
    assert second_response.status_code == 202

    first_job_id = first_response.json()["job_id"]
    second_job_id = second_response.json()["job_id"]

    second_job = test_client.get(f"/jobs/{second_job_id}").json()
    recipient_id = second_job["recipients"][0]["recipient_id"]

    response = test_client.get(
        f"/jobs/{first_job_id}/recipients/{recipient_id}/certificate"
    )

    assert response.status_code == 404
