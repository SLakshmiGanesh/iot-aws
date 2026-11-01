from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app import main


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "DB_PATH", tmp_path / "telemetry.sqlite3")
    with TestClient(main.app) as test_client:
        yield test_client


def sample_reading(**overrides):
    reading = {
        "device_id": "sensor-test",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "temperature": 24.5,
        "humidity": 45,
        "air_quality": 80,
        "status": "online",
    }
    reading.update(overrides)
    return reading


def test_health_and_readiness(client):
    assert client.get("/health").json()["status"] == "ok"
    assert client.get("/ready").json()["status"] == "ready"


def test_seeded_summary_and_request_id(client):
    response = client.get("/api/v1/analytics/summary", headers={"X-Request-ID": "test-request-123"})
    assert response.status_code == 200
    assert response.json()["device_count"] == 1
    assert response.headers["X-Request-ID"] == "test-request-123"


def test_validation_rejects_out_of_range_and_naive_timestamps(client):
    response = client.post("/api/v1/telemetry", json=sample_reading(temperature=200))
    assert response.status_code == 422

    response = client.post("/api/v1/telemetry", json=sample_reading(timestamp="2026-11-01T10:00:00"))
    assert response.status_code == 422


def test_invalid_status_is_rejected(client):
    response = client.post("/api/v1/telemetry", json=sample_reading(status="unknown"))
    assert response.status_code == 422


def test_duplicate_readings_are_idempotent_and_persist_between_requests(client):
    payload = sample_reading(timestamp="2026-11-01T10:00:00+00:00")
    first = client.post("/api/v1/telemetry", json=payload)
    duplicate = client.post("/api/v1/telemetry", json=payload)

    assert first.status_code == 201
    assert first.json()["stored"] is True
    assert duplicate.status_code == 201
    assert duplicate.json()["stored"] is False
    result = client.get("/api/v1/devices/sensor-test/telemetry")
    assert result.status_code == 200
    assert len(result.json()["items"]) == 1


def test_time_range_must_be_ordered_and_timezone_aware(client):
    response = client.get(
        "/api/v1/devices/sensor-test/telemetry",
        params={"since": "2026-11-02T00:00:00Z", "until": "2026-11-01T00:00:00Z"},
    )
    assert response.status_code == 400

    response = client.get(
        "/api/v1/devices/sensor-test/telemetry",
        params={"since": "2026-11-01T00:00:00"},
    )
    assert response.status_code == 400


def test_non_demo_ingestion_requires_token(client, monkeypatch):
    monkeypatch.setattr(main, "DEMO_MODE", False)
    monkeypatch.setattr(main, "INGESTION_API_TOKEN", "test-only-token")
    payload = sample_reading(timestamp="2026-11-01T11:00:00+00:00")

    denied = client.post("/api/v1/telemetry", json=payload)
    assert denied.status_code == 401

    accepted = client.post(
        "/api/v1/telemetry",
        json=payload,
        headers={"X-Ingestion-Token": "test-only-token"},
    )
    assert accepted.status_code == 201
    assert accepted.json()["stored"] is True
