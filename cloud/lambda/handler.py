"""AWS IoT telemetry rule target. Validates, classifies, and stores each reading."""
import json
import os
from datetime import datetime, timezone
from decimal import Decimal

import boto3
from botocore.exceptions import BotoCoreError, ClientError

TABLE_NAME = os.environ.get("TABLE_NAME")
DEVICES_TABLE_NAME = os.environ.get("DEVICES_TABLE_NAME")
HOME_ID = os.environ.get("HOME_ID", "demo-home")


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
    return parsed.isoformat(timespec="microseconds").replace("+00:00", "Z")


def handler(event, context):
    if not isinstance(event, dict):
        raise ValueError("event must be an object")
    device = event.get("device_id")
    if not isinstance(device, str) or not 1 <= len(device) <= 64:
        raise ValueError("invalid device_id")

    item = {
        "device_id": device,
        "timestamp": _timestamp(event.get("timestamp")),
        "temperature": _number(event.get("temperature"), "temperature", -40, 85),
        "humidity": _number(event.get("humidity"), "humidity", 0, 100),
        "air_quality": int(_number(event.get("air_quality"), "air_quality", 0, 10000)),
        "status": event.get("status", "online"),
    }
    if item["status"] not in ("online", "offline"):
        raise ValueError("invalid status")

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

    if not TABLE_NAME or not DEVICES_TABLE_NAME:
        raise RuntimeError("TABLE_NAME and DEVICES_TABLE_NAME must be configured")
    dynamodb = boto3.resource("dynamodb")
    try:
        dynamodb.Table(TABLE_NAME).put_item(Item=item)
        dynamodb.Table(DEVICES_TABLE_NAME).update_item(
            Key={"home_id": HOME_ID, "device_id": device},
            UpdateExpression="SET #ts=:ts, temperature=:temperature, humidity=:humidity, air_quality=:air_quality, #status=:status, alert_status=:alert_status",
            ConditionExpression="attribute_not_exists(#ts) OR #ts < :ts",
            ExpressionAttributeNames={"#ts": "timestamp", "#status": "status"},
            ExpressionAttributeValues={
                ":ts": item["timestamp"],
                ":temperature": item["temperature"],
                ":humidity": item["humidity"],
                ":air_quality": item["air_quality"],
                ":status": item["status"],
                ":alert_status": item["alert_status"],
            },
        )
    except ClientError as error:
        if error.response.get("Error", {}).get("Code") != "ConditionalCheckFailedException":
            print(json.dumps({"event": "telemetry_write_failed", "device_id": device}))
            raise
    except BotoCoreError:
        print(json.dumps({"event": "telemetry_write_failed", "device_id": device}))
        raise

    print(json.dumps({
        "event": "telemetry_processed",
        "device_id": device,
        "alert_status": item["alert_status"],
    }))
    return {"stored": True, "device_id": device, "alert_status": item["alert_status"]}
