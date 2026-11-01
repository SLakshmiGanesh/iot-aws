"""AWS IoT telemetry rule target with strict validation and idempotent writes."""
import hashlib
import json
import os
import re
from datetime import datetime, timezone, timedelta
from decimal import Decimal

import boto3
from botocore.exceptions import BotoCoreError, ClientError

TABLE_NAME = os.environ.get("TABLE_NAME")
DEVICES_TABLE_NAME = os.environ.get("DEVICES_TABLE_NAME")
HOME_ID = os.environ.get("HOME_ID", "demo-home")
DEVICE_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
MAX_REPLAY_AGE = timedelta(days=int(os.getenv("MAX_REPLAY_AGE_DAYS", "7")))
MAX_FUTURE_SKEW = timedelta(minutes=int(os.getenv("MAX_FUTURE_SKEW_MINUTES", "5")))


def _number(value, name, low, high):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not low <= value <= high:
        raise ValueError(f"{name} out of range")
    return Decimal(str(value))


def _timestamp(value):
    if not isinstance(value, str):
        raise ValueError("invalid timestamp")
    try:
        if value.isdigit():
            epoch = int(value)
            if epoch > 10**12:
                epoch /= 1000
            parsed = datetime.fromtimestamp(epoch, timezone.utc)
        else:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                raise ValueError("timestamp must include a timezone")
            parsed = parsed.astimezone(timezone.utc)
    except (ValueError, OverflowError, OSError):
        raise ValueError("invalid timestamp")
    now = datetime.now(timezone.utc)
    if parsed < now - MAX_REPLAY_AGE or parsed > now + MAX_FUTURE_SKEW:
        raise ValueError("timestamp outside accepted replay window")
    return parsed.isoformat(timespec="microseconds").replace("+00:00", "Z")


def _valid_device(device):
    return isinstance(device, str) and DEVICE_PATTERN.fullmatch(device) is not None


def _log(event, **fields):
    print(json.dumps({"event": event, **fields}, separators=(",", ":")))


def handler(event, context):
    if not isinstance(event, dict):
        raise ValueError("event must be an object")
    request_id = getattr(context, "aws_request_id", None)
    device = event.get("device_id")
    if not _valid_device(device):
        raise ValueError("invalid device_id")
    if event.get("topic_device_id", device) != device:
        raise ValueError("payload device_id does not match MQTT topic")
    home_id = event.get("home_id", HOME_ID)
    if not isinstance(home_id, str) or home_id != HOME_ID:
        raise ValueError("message is outside the configured home")

    timestamp = _timestamp(event.get("timestamp"))
    item = {
        "home_id": home_id,
        "device_id": device,
        "timestamp": timestamp,
        "temperature": _number(event.get("temperature"), "temperature", -40, 85),
        "humidity": _number(event.get("humidity"), "humidity", 0, 100),
        "air_quality": int(_number(event.get("air_quality"), "air_quality", 0, 10000)),
        "status": event.get("status", "online"),
    }
    if item["status"] not in ("online", "offline"):
        raise ValueError("invalid status")

    supplied_event_id = event.get("event_id")
    if supplied_event_id is not None and (
        not isinstance(supplied_event_id, str)
        or not 1 <= len(supplied_event_id) <= 128
        or not re.fullmatch(r"[A-Za-z0-9_-]+", supplied_event_id)
    ):
        raise ValueError("invalid event_id")
    digest_input = "|".join(str(item[key]) for key in (
        "home_id", "device_id", "timestamp", "temperature", "humidity", "air_quality"
    ))
    item["event_id"] = supplied_event_id or hashlib.sha256(digest_input.encode()).hexdigest()

    temp_warning = float(os.getenv("TEMP_WARNING", "30"))
    temp_critical = float(os.getenv("TEMP_CRITICAL", "35"))
    humidity_warning = float(os.getenv("HUMIDITY_WARNING", "60"))
    humidity_critical = float(os.getenv("HUMIDITY_CRITICAL", "75"))
    temperature = float(item["temperature"])
    humidity = float(item["humidity"])
    item["alert_status"] = (
        "critical" if temperature >= temp_critical or humidity >= humidity_critical
        else "warning" if temperature >= temp_warning or humidity >= humidity_warning
        else "normal"
    )

    retention_days = int(os.getenv("TTL_DAYS", "90"))
    expires_at = datetime.fromisoformat(timestamp.replace("Z", "+00:00")) + timedelta(days=retention_days)
    item["expires_at"] = int(expires_at.timestamp())

    if not TABLE_NAME or not DEVICES_TABLE_NAME:
        raise RuntimeError("TABLE_NAME and DEVICES_TABLE_NAME must be configured")
    dynamodb = boto3.resource("dynamodb")
    duplicate = False
    try:
        dynamodb.Table(TABLE_NAME).put_item(
            Item=item,
            ConditionExpression="attribute_not_exists(device_id)",
        )
    except ClientError as error:
        if error.response.get("Error", {}).get("Code") != "ConditionalCheckFailedException":
            _log("telemetry_write_failed", request_id=request_id, device_id=device)
            raise
        duplicate = True
        _log("duplicate_telemetry_ignored", request_id=request_id, device_id=device, event_id=item["event_id"])
    except BotoCoreError:
        _log("telemetry_write_failed", device_id=device)
        raise

    try:
        dynamodb.Table(DEVICES_TABLE_NAME).update_item(
            Key={"home_id": home_id, "device_id": device},
            UpdateExpression="SET #ts=:ts, temperature=:temperature, humidity=:humidity, air_quality=:air_quality, #status=:status, alert_status=:alert_status",
            ConditionExpression="attribute_not_exists(#ts) OR #ts < :ts",
            ExpressionAttributeNames={"#ts": "timestamp", "#status": "status"},
            ExpressionAttributeValues={
                ":ts": timestamp,
                ":temperature": item["temperature"],
                ":humidity": item["humidity"],
                ":air_quality": item["air_quality"],
                ":status": item["status"],
                ":alert_status": item["alert_status"],
            },
        )
    except ClientError as error:
        code = error.response.get("Error", {}).get("Code")
        if code == "ConditionalCheckFailedException":
            _log("stale_latest_reading_ignored", request_id=request_id, device_id=device, timestamp=timestamp)
        else:
            _log("device_registry_update_failed", request_id=request_id, device_id=device)
            raise
    except BotoCoreError:
        _log("device_registry_update_failed", device_id=device)
        raise

    _log("telemetry_processed", request_id=request_id, device_id=device, event_id=item["event_id"], alert_status=item["alert_status"], duplicate=duplicate)
    return {"stored": not duplicate, "device_id": device, "event_id": item["event_id"], "alert_status": item["alert_status"]}


def status_handler(event, context):
    """Update online/offline status from AWS IoT status and Last Will topics."""
    if not isinstance(event, dict):
        raise ValueError("status event must be an object")
    request_id = getattr(context, "aws_request_id", None)
    device = event.get("device_id")
    status = event.get("status")
    if not _valid_device(device):
        raise ValueError("invalid device_id")
    if event.get("topic_device_id", device) != device:
        raise ValueError("payload device_id does not match MQTT topic")
    home_id = event.get("home_id", HOME_ID)
    if home_id != HOME_ID:
        raise ValueError("status event is outside the configured home")
    if status not in ("online", "offline"):
        raise ValueError("invalid device status")
    if not DEVICES_TABLE_NAME:
        raise RuntimeError("DEVICES_TABLE_NAME must be configured")

    updated_at = _timestamp(event["timestamp"]) if event.get("timestamp") else datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")
    try:
        boto3.resource("dynamodb").Table(DEVICES_TABLE_NAME).update_item(
            Key={"home_id": home_id, "device_id": device},
            UpdateExpression="SET #status=:status, last_status_at=:updated_at",
            ConditionExpression="attribute_exists(home_id) AND (attribute_not_exists(last_status_at) OR last_status_at <= :updated_at)",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={":status": status, ":updated_at": updated_at},
        )
    except ClientError as error:
        code = error.response.get("Error", {}).get("Code")
        if code == "ConditionalCheckFailedException":
            _log("stale_or_unregistered_status_ignored", request_id=request_id, device_id=device)
            return {"updated": False, "device_id": device}
        _log("device_status_update_failed", request_id=request_id, device_id=device)
        raise
    except BotoCoreError:
        _log("device_status_update_failed", device_id=device)
        raise

    _log("device_status_updated", request_id=request_id, device_id=device, status=status)
    return {"updated": True, "device_id": device, "status": status}
