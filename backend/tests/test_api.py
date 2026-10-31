import os
os.environ["DATABASE_PATH"] = ":memory:"
from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)
def test_health(): assert client.get("/health").json()["status"]=="ok"
def test_summary(): assert client.get("/api/v1/analytics/summary").status_code==200
def test_validation():
    response=client.post("/api/v1/telemetry",json={"device_id":"sensor","timestamp":"2026-10-31T10:00:00Z","temperature":200,"humidity":30,"air_quality":20})
    assert response.status_code==422
