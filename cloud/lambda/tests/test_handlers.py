import json
import os
import sys
from pathlib import Path

os.environ.setdefault("AWS_EC2_METADATA_DISABLED", "true")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "test")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test")
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("TABLE_NAME", "telemetry-test")
os.environ.setdefault("DEVICES_TABLE_NAME", "devices-test")
os.environ.setdefault("HOME_ID", "home-test")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import api_handler
import handler as processor


class FakeTable:
    def __init__(self, items=None):
        self.items = items or []
        self.writes = []
    def put_item(self, **kwargs):
        self.writes.append(kwargs["Item"])
    def query(self, **kwargs):
        return {"Items": self.items}
    def get_item(self, **kwargs):
        return {"Item": self.items[0]} if self.items else {}


class FakeDynamo:
    def __init__(self, tables):
        self.tables = tables
    def Table(self, name):
        return self.tables[name]


def sample_event():
    return {
        "device_id": "sensor-1",
        "timestamp": "1700000000",
        "temperature": 32,
        "humidity": 55,
        "air_quality": 110,
        "status": "online",
    }


def test_processor_persists_telemetry_and_device_registry(monkeypatch):
    telemetry = FakeTable()
    devices = FakeTable()
    monkeypatch.setattr(
        processor.boto3, "resource",
        lambda _: FakeDynamo({"telemetry-test": telemetry, "devices-test": devices}),
    )
    result = processor.handler(sample_event(), None)
    assert result == {"stored": True, "device_id": "sensor-1", "alert_status": "warning"}
    assert telemetry.writes[0]["timestamp"].endswith("Z")
    assert devices.writes[0]["home_id"] == "home-test"


def test_processor_rejects_out_of_range_sensor_value(monkeypatch):
    event = sample_event()
    event["humidity"] = 140
    monkeypatch.setattr(processor.boto3, "resource", lambda _: FakeDynamo({"telemetry-test": FakeTable(), "devices-test": FakeTable()}))
    try:
        processor.handler(event, None)
        assert False, "expected validation error"
    except ValueError as error:
        assert "humidity" in str(error)


def test_read_api_returns_device_summary(monkeypatch):
    api_handler.devices_table = FakeTable([{
        "device_id": "sensor-1",
        "temperature": 24,
        "humidity": 45,
        "air_quality": 95,
        "alert_status": "normal",
        "timestamp": "2026-10-31T10:00:00Z",
    }])
    response = api_handler.handler({
        "rawPath": "/api/v1/analytics/summary",
        "requestContext": {"http": {"method": "GET"}},
    }, None)
    body = json.loads(response["body"])
    assert response["statusCode"] == 200
    assert body["device_count"] == 1
    assert body["temperature"] == 24


def test_read_api_rejects_unknown_route():
    response = api_handler.handler({
        "rawPath": "/private",
        "requestContext": {"http": {"method": "GET"}},
    }, None)
    assert response["statusCode"] == 404
