"""Read-only HTTP API for the monitoring dashboard (API Gateway HTTP API v2)."""
from __future__ import annotations

import json
import os
from decimal import Decimal
from typing import Any
from urllib.parse import unquote

import boto3
from boto3.dynamodb.conditions import Key

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


def _query_history(device_id: str, params: dict[str, str]) -> dict[str, Any]:
    try:
        limit = max(1, min(500, int(params.get("limit", "100"))))
    except ValueError:
        return _response(400, {"error": {"code": "invalid_limit", "message": "limit must be an integer"}})

    key_condition = Key("device_id").eq(device_id)
    since, until = params.get("since"), params.get("until")
    if since and until:
        key_condition &= Key("timestamp").between(since, until)
    elif since:
        key_condition &= Key("timestamp").gte(since)
    elif until:
        key_condition &= Key("timestamp").lte(until)
    result = telemetry.query(
        KeyConditionExpression=key_condition,
        ScanIndexForward=False,
        Limit=limit,
    )
    return _response(200, {"items": list(reversed(result.get("Items", []))), "limit": limit})


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    request = event.get("requestContext", {}).get("http", {})
    method = request.get("method", "GET").upper()
    path = event.get("rawPath", "/")
    params = event.get("queryStringParameters") or {}

    if method == "GET" and path == "/health":
        return _response(200, {"status": "ok", "mode": "aws"})
    if method == "GET" and path == "/api/v1/devices":
        result = devices_table.query(
            KeyConditionExpression=Key("home_id").eq(HOME_ID),
            Limit=200,
        )
        return _response(200, {"items": result.get("Items", []), "total": len(result.get("Items", []))})
    if method == "GET" and path == "/api/v1/analytics/summary":
        result = devices_table.query(
            KeyConditionExpression=Key("home_id").eq(HOME_ID),
            Limit=200,
        )
        items = result.get("Items", [])
        count = max(1, len(items))
        return _response(200, {
            "device_count": sum(1 for item in items if item.get("status", "online") == "online"),
            "registered_device_count": len(items),
            "temperature": round(sum(float(x.get("temperature", 0)) for x in items) / count, 1),
            "humidity": round(sum(float(x.get("humidity", 0)) for x in items) / count, 1),
            "air_quality": round(sum(float(x.get("air_quality", 0)) for x in items) / count, 1),
            "alert_count": sum(1 for x in items if x.get("alert_status", "normal") != "normal"),
            "updated_at": max((x.get("timestamp", "") for x in items), default=None),
        })
    if method == "GET" and path == "/api/v1/analytics/history":
        devices = devices_table.query(
            KeyConditionExpression=Key("home_id").eq(HOME_ID),
            Limit=1,
        ).get("Items", [])
        if not devices:
            return _response(200, {"items": [], "limit": 0})
        return _query_history(devices[0]["device_id"], params)
    if method == "GET" and path == "/api/v1/alerts":
        alerts = []
        for status in ("warning", "critical"):
            result = telemetry.query(
                IndexName="alert-status-timestamp-index",
                KeyConditionExpression=Key("alert_status").eq(status),
                ScanIndexForward=False,
                Limit=50,
            )
            alerts.extend(result.get("Items", []))
        alerts.sort(key=lambda row: row.get("timestamp", ""), reverse=True)
        return _response(200, {"items": alerts[:100]})

    prefix = "/api/v1/devices/"
    if method == "GET" and path.startswith(prefix):
        suffix = path[len(prefix):].strip("/").split("/")
        device_id = unquote(suffix[0]) if suffix and suffix[0] else ""
        if len(suffix) >= 2 and suffix[1] == "telemetry":
            if len(suffix) == 3 and suffix[2] == "latest":
                result = telemetry.query(
                    KeyConditionExpression=Key("device_id").eq(device_id),
                    ScanIndexForward=False,
                    Limit=1,
                )
                items = result.get("Items", [])
                return _response(200, items[0]) if items else _response(404, {"error": {"code": "not_found", "message": "No telemetry for device"}})
            return _query_history(device_id, params)
        result = devices_table.get_item(Key={"home_id": HOME_ID, "device_id": device_id})
        item = result.get("Item")
        return _response(200, item) if item else _response(404, {"error": {"code": "not_found", "message": "Device not found"}})

    return _response(404, {"error": {"code": "not_found", "message": "Route not found"}})
