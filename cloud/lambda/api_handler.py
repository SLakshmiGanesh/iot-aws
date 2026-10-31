"""Read-only, home-scoped HTTP API for API Gateway HTTP API v2."""
from __future__ import annotations

import base64
import json
import os
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from urllib.parse import unquote

import boto3
from boto3.dynamodb.conditions import Attr, Key

TABLE_NAME = os.environ["TABLE_NAME"]
DEVICES_TABLE_NAME = os.environ["DEVICES_TABLE_NAME"]
HOME_ID = os.getenv("HOME_ID", "demo-home")
dynamodb = boto3.resource("dynamodb")
telemetry = dynamodb.Table(TABLE_NAME)
devices_table = dynamodb.Table(DEVICES_TABLE_NAME)


def _json_default(value: Any):
    if isinstance(value, Decimal):
        return int(value) if value % 1 == 0 else float(value)
    raise TypeError(f"Cannot JSON encode {type(value).__name__}")


def _response(status: int, body: Any) -> dict[str, Any]:
    return {
        "statusCode": status,
        "headers": {"content-type": "application/json; charset=utf-8"},
        "body": json.dumps(body, default=_json_default),
    }


def _decode_token(value: str | None) -> dict[str, Any] | None:
    if not value:
        return None
    try:
        decoded = json.loads(base64.urlsafe_b64decode(value.encode() + b"==="))
        return decoded if isinstance(decoded, dict) else None
    except (ValueError, TypeError, json.JSONDecodeError):
        return None


def _encode_token(key: dict[str, Any] | None) -> str | None:
    if not key:
        return None
    return base64.urlsafe_b64encode(json.dumps(key, default=_json_default).encode()).decode().rstrip("=")


def _query_devices(limit: int = 200) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    items: list[dict[str, Any]] = []
    key = None
    while len(items) < limit:
        kwargs: dict[str, Any] = {
            "KeyConditionExpression": Key("home_id").eq(HOME_ID),
            "Limit": min(100, limit - len(items)),
        }
        if key:
            kwargs["ExclusiveStartKey"] = key
        result = devices_table.query(**kwargs)
        items.extend(result.get("Items", []))
        key = result.get("LastEvaluatedKey")
        if not key:
            break
    return items[:limit], key


def _device_exists(device_id: str) -> bool:
    result = devices_table.get_item(
        Key={"home_id": HOME_ID, "device_id": device_id},
        ProjectionExpression="device_id",
    )
    return "Item" in result


def _query_history(device_id: str, params: dict[str, str]) -> dict[str, Any]:
    try:
        limit = int(params.get("limit", "100"))
        if not 1 <= limit <= 500:
            raise ValueError
    except (TypeError, ValueError):
        return _response(400, {"error": {"code": "invalid_limit", "message": "limit must be between 1 and 500"}})

    since, until = params.get("since"), params.get("until")
    try:
        for value in (since, until):
            if value:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
                if parsed.tzinfo is None:
                    raise ValueError
        if since and until and datetime.fromisoformat(since.replace("Z", "+00:00")) > datetime.fromisoformat(until.replace("Z", "+00:00")):
            raise ValueError
    except ValueError:
        return _response(400, {"error": {"code": "invalid_time_range", "message": "since and until must be timezone-aware ISO timestamps with since <= until"}})

    condition = Key("device_id").eq(device_id)
    if since and until:
        condition &= Key("timestamp").between(since, until)
    elif since:
        condition &= Key("timestamp").gte(since)
    elif until:
        condition &= Key("timestamp").lte(until)

    items: list[dict[str, Any]] = []
    key = _decode_token(params.get("next_token"))
    while len(items) < limit:
        kwargs: dict[str, Any] = {
            "KeyConditionExpression": condition,
            "FilterExpression": Attr("home_id").eq(HOME_ID),
            "ScanIndexForward": False,
            "Limit": min(100, limit - len(items)),
        }
        if key:
            kwargs["ExclusiveStartKey"] = key
        result = telemetry.query(**kwargs)
        items.extend(result.get("Items", []))
        key = result.get("LastEvaluatedKey")
        if not key:
            break
    page = items[:limit]
    page.reverse()
    return _response(200, {"items": page, "limit": limit, "next_token": _encode_token(key)})


def _query_alerts(limit: int) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []
    for status in ("warning", "critical"):
        key = None
        while len(alerts) < limit:
            kwargs: dict[str, Any] = {
                "IndexName": "alert-status-timestamp-index",
                "KeyConditionExpression": Key("alert_status").eq(status),
                "FilterExpression": Attr("home_id").eq(HOME_ID),
                "ScanIndexForward": False,
                "Limit": min(100, limit - len(alerts)),
            }
            if key:
                kwargs["ExclusiveStartKey"] = key
            result = telemetry.query(**kwargs)
            alerts.extend(result.get("Items", []))
            key = result.get("LastEvaluatedKey")
            if not key:
                break
    alerts.sort(key=lambda row: row.get("timestamp", ""), reverse=True)
    return alerts[:limit]


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    request = event.get("requestContext", {}).get("http", {})
    method = request.get("method", "GET").upper()
    path = event.get("rawPath", "/")
    params = event.get("queryStringParameters") or {}

    if method == "GET" and path == "/health":
        return _response(200, {"status": "ok", "mode": "aws"})
    if method == "GET" and path == "/api/v1/devices":
        items, next_key = _query_devices(200)
        return _response(200, {"items": items, "total": len(items), "next_token": _encode_token(next_key)})
    if method == "GET" and path == "/api/v1/analytics/summary":
        items, _ = _query_devices(200)
        count = max(1, len(items))
        return _response(200, {
            "device_count": sum(1 for item in items if item.get("status") == "online"),
            "registered_device_count": len(items),
            "temperature": round(sum(float(x.get("temperature", 0)) for x in items) / count, 1),
            "humidity": round(sum(float(x.get("humidity", 0)) for x in items) / count, 1),
            "air_quality": round(sum(float(x.get("air_quality", 0)) for x in items) / count, 1),
            "alert_count": sum(1 for x in items if x.get("alert_status", "normal") != "normal"),
            "updated_at": max((x.get("timestamp", "") for x in items), default=None),
        })
    if method == "GET" and path == "/api/v1/analytics/history":
        devices, _ = _query_devices(1)
        if not devices:
            return _response(200, {"items": [], "limit": 0, "next_token": None})
        return _query_history(devices[0]["device_id"], params)
    if method == "GET" and path == "/api/v1/alerts":
        try:
            limit = int(params.get("limit", "100"))
            if not 1 <= limit <= 500:
                raise ValueError
        except (TypeError, ValueError):
            return _response(400, {"error": {"code": "invalid_limit", "message": "limit must be between 1 and 500"}})
        return _response(200, {"items": _query_alerts(limit)})

    prefix = "/api/v1/devices/"
    if method == "GET" and path.startswith(prefix):
        suffix = path[len(prefix):].strip("/").split("/")
        device_id = unquote(suffix[0]) if suffix and suffix[0] else ""
        if not device_id or len(device_id) > 64:
            return _response(400, {"error": {"code": "invalid_device_id", "message": "Invalid device identifier"}})
        if not _device_exists(device_id):
            return _response(404, {"error": {"code": "not_found", "message": "Device not found"}})
        if len(suffix) >= 2 and suffix[1] == "telemetry":
            if len(suffix) == 3 and suffix[2] == "latest":
                result = telemetry.query(
                    KeyConditionExpression=Key("device_id").eq(device_id),
                    FilterExpression=Attr("home_id").eq(HOME_ID),
                    ScanIndexForward=False,
                    Limit=100,
                )
                items = result.get("Items", [])
                if items:
                    return _response(200, max(items, key=lambda item: item.get("timestamp", "")))
                return _response(404, {"error": {"code": "not_found", "message": "No telemetry for device"}})
            return _query_history(device_id, params)
        result = devices_table.get_item(Key={"home_id": HOME_ID, "device_id": device_id})
        item = result.get("Item")
        return _response(200, item) if item else _response(404, {"error": {"code": "not_found", "message": "Device not found"}})

    return _response(404, {"error": {"code": "not_found", "message": "Route not found"}})
