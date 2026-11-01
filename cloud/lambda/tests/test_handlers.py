import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from botocore.exceptions import ClientError

os.environ.setdefault("AWS_EC2_METADATA_DISABLED", "true")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "test")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test")
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("TABLE_NAME", "telemetry-test")
os.environ.setdefault("DEVICES_TABLE_NAME", "devices-test")
os.environ.setdefault("HOME_ID", "home-test")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import api_handler  # noqa: E402
import handler as processor  # noqa: E402


class FakeTable:
    def __init__(self, items=None):
        self.items = items or []
        self.writes = []
        self.queries = []
        self.put_error = None

    def put_item(self, **kwargs):
        if self.put_error:
            raise self.put_error
        self.writes.append(kwargs["Item"])

    def update_item(self, **kwargs):
        self.writes.append(kwargs)

    def query(self, **kwargs):
        self.queries.append(kwargs)
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
        "home_id": "home-test",
        "topic_device_id": "sensor-1",
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "temperature": 32,
        "humidity": 55,
        "air_quality": 110,
        "status": "online",
    }


def test_processor_persists_home_scope_and_idempotency_metadata(monkeypatch):
    telemetry = FakeTable()
    devices = FakeTable()
    monkeypatch.setattr(
        processor.boto3, "resource",
        lambda _: FakeDynamo({"telemetry-test": telemetry, "devices-test": devices}),
    )
    result = processor.handler(sample_event(), None)
    assert result["stored"] is True
    assert result["alert_status"] == "warning"
    assert telemetry.writes[0]["home_id"] == "home-test"
    assert telemetry.writes[0]["event_id"]
    assert telemetry.writes[0]["timestamp"].endswith("Z")
    assert devices.writes[0]["Key"] == {"home_id": "home-test", "device_id": "sensor-1"}
    assert devices.writes[0]["ConditionExpression"] == "attribute_not_exists(#ts) OR #ts < :ts"


def test_processor_rejects_out_of_range_sensor_value(monkeypatch):
    event = sample_event()
    event["humidity"] = 140
    monkeypatch.setattr(processor.boto3, "resource", lambda _: FakeDynamo({"telemetry-test": FakeTable(), "devices-test": FakeTable()}))
    try:
        processor.handler(event, None)
        assert False, "expected validation error"
    except ValueError as error:
        assert "humidity" in str(error)


def test_processor_rejects_topic_identity_and_home_mismatch():
    event = sample_event()
    event["topic_device_id"] = "other-device"
    try:
        processor.handler(event, None)
        assert False, "expected topic identity validation error"
    except ValueError as error:
        assert "topic" in str(error)

    event = sample_event()
    event["home_id"] = "another-home"
    try:
        processor.handler(event, None)
        assert False, "expected home validation error"
    except ValueError as error:
        assert "home" in str(error)


def test_processor_rejects_replayed_timestamp():
    event = sample_event()
    event["timestamp"] = "1700000000"
    try:
        processor.handler(event, None)
        assert False, "expected timestamp replay validation error"
    except ValueError as error:
        assert "replay window" in str(error)


def test_read_api_returns_device_summary_and_home_query(monkeypatch):
    devices = FakeTable([{
        "device_id": "sensor-1",
        "temperature": 24,
        "humidity": 45,
        "air_quality": 95,
        "alert_status": "normal",
        "timestamp": "2026-10-31T10:00:00Z",
        "status": "online",
    }])
    api_handler.devices_table = devices
    response = api_handler.handler({
        "rawPath": "/api/v1/analytics/summary",
        "requestContext": {"http": {"method": "GET"}},
    }, None)
    body = json.loads(response["body"])
    assert response["statusCode"] == 200
    assert body["device_count"] == 1
    assert body["temperature"] == 24
    assert devices.queries[0]["KeyConditionExpression"] is not None


def test_read_api_rejects_unknown_route():
    response = api_handler.handler({
        "rawPath": "/private",
        "requestContext": {"http": {"method": "GET"}},
    }, None)
    assert response["statusCode"] == 404


def test_status_handler_updates_presence(monkeypatch):
    devices = FakeTable([{"device_id": "sensor-1"}])
    monkeypatch.setattr(
        processor.boto3, "resource",
        lambda _: FakeDynamo({"devices-test": devices}),
    )
    result = processor.status_handler({
        "device_id": "sensor-1",
        "home_id": "home-test",
        "topic_device_id": "sensor-1",
        "status": "offline",
    }, None)
    assert result["updated"] is True
    assert devices.writes[0]["Key"] == {"home_id": "home-test", "device_id": "sensor-1"}
    assert devices.writes[0]["ExpressionAttributeValues"][":status"] == "offline"


def test_duplicate_telemetry_is_reported_without_overwriting(monkeypatch):
    telemetry = FakeTable()
    telemetry.put_error = ClientError(
        {"Error": {"Code": "ConditionalCheckFailedException", "Message": "duplicate"}},
        "PutItem",
    )
    devices = FakeTable()
    monkeypatch.setattr(
        processor.boto3, "resource",
        lambda _: FakeDynamo({"telemetry-test": telemetry, "devices-test": devices}),
    )
    result = processor.handler(sample_event(), None)
    assert result["stored"] is False
    assert result["device_id"] == "sensor-1"
    assert len(devices.writes) == 1


def test_read_api_rejects_invalid_pagination_tokens():
    response = api_handler.handler({
        "rawPath": "/api/v1/devices",
        "queryStringParameters": {"next_token": "not-a-valid-token"},
        "requestContext": {"http": {"method": "GET"}},
    }, None)
    assert response["statusCode"] == 400

    api_handler.devices_table = FakeTable([{"device_id": "sensor-1"}])
    response = api_handler.handler({
        "rawPath": "/api/v1/devices/sensor-1/telemetry",
        "queryStringParameters": {"next_token": "not-a-valid-token"},
        "requestContext": {"http": {"method": "GET"}},
    }, None)
    assert response["statusCode"] == 400
