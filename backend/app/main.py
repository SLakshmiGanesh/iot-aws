from __future__ import annotations

import hmac
import json
import logging
import os
import sqlite3
import uuid
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator, Literal

from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field, field_validator

DB_PATH = Path(os.getenv("DATABASE_PATH", "/data/telemetry.db"))
APP_MODE = os.getenv("APP_MODE", "local")
DEMO_MODE = APP_MODE == "local"
INGESTION_API_TOKEN = os.getenv("INGESTION_API_TOKEN")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(message)s")
log = logging.getLogger("iot_api")


class Reading(BaseModel):
    model_config = ConfigDict(extra="forbid")
    device_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    timestamp: datetime
    temperature: float = Field(ge=-40, le=85)
    humidity: float = Field(ge=0, le=100)
    air_quality: int = Field(ge=0, le=10000)
    status: Literal["online", "offline"] = "online"

    @field_validator("timestamp")
    @classmethod
    def timestamp_must_have_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must include a timezone")
        return value.astimezone(timezone.utc)


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH, timeout=5)
    db.row_factory = sqlite3.Row
    db.execute(
        """CREATE TABLE IF NOT EXISTS telemetry (
          device_id TEXT NOT NULL, timestamp TEXT NOT NULL, temperature REAL NOT NULL,
          humidity REAL NOT NULL, air_quality INTEGER NOT NULL, status TEXT NOT NULL,
          alert_status TEXT NOT NULL, PRIMARY KEY(device_id, timestamp))"""
    )
    return db


@contextmanager
def connection() -> Iterator[sqlite3.Connection]:
    db = connect()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def seed() -> None:
    with connection() as db:
        if db.execute("SELECT COUNT(*) FROM telemetry").fetchone()[0]:
            return
        now = datetime.now(timezone.utc)
        import math

        for idx in range(48):
            timestamp = now - timedelta(minutes=idx * 15)
            db.execute(
                "INSERT INTO telemetry VALUES(?,?,?,?,?,?,?)",
                (
                    "home-sensor-01",
                    timestamp.isoformat(),
                    round(23 + 2 * math.sin(idx / 5), 1),
                    round(47 + 8 * math.sin(idx / 7), 1),
                    85 + idx % 24,
                    "online",
                    "normal",
                ),
            )


@asynccontextmanager
async def lifespan(app: FastAPI):
    if DEMO_MODE:
        seed()
    yield


app = FastAPI(title="Home Environmental Monitor API", version="1.1.0", lifespan=lifespan)
origins = [x.strip() for x in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if x.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["GET", "POST"],
    allow_headers=["content-type", "x-ingestion-token", "x-request-id"],
)


@app.middleware("http")
async def request_context(request: Request, call_next):
    supplied = request.headers.get("x-request-id", "")
    request_id = supplied if 0 < len(supplied) <= 128 else str(uuid.uuid4())
    request.state.request_id = request_id
    try:
        response = await call_next(request)
    except Exception:
        log.exception(json.dumps({"event": "request_failed", "request_id": request_id}))
        raise
    response.headers["X-Request-ID"] = request_id
    return response


def _utc_iso(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise HTTPException(400, detail={"code": "invalid_timestamp", "message": "Timestamp must include a timezone"})
    return value.astimezone(timezone.utc).isoformat()


@app.get("/health")
def health():
    return {"status": "ok", "mode": "local-demo" if DEMO_MODE else "configured"}


@app.get("/ready")
def ready():
    try:
        with connection() as db:
            db.execute("SELECT 1").fetchone()
    except sqlite3.Error:
        log.exception(json.dumps({"event": "readiness_check_failed"}))
        raise HTTPException(503, detail={"code": "database_unavailable", "message": "Storage is not ready"})
    return {"status": "ready"}


@app.get("/api/v1/devices")
def devices():
    with connection() as db:
        rows = db.execute(
            "SELECT device_id, MAX(timestamp) latest, COUNT(*) reading_count FROM telemetry GROUP BY device_id ORDER BY device_id"
        ).fetchall()
    return {"items": [dict(row) for row in rows], "total": len(rows)}


@app.get("/api/v1/devices/{device_id}")
def device(device_id: str):
    with connection() as db:
        row = db.execute(
            "SELECT device_id, MAX(timestamp) latest, COUNT(*) reading_count FROM telemetry WHERE device_id=? GROUP BY device_id",
            (device_id,),
        ).fetchone()
    if not row:
        raise HTTPException(404, detail={"code": "device_not_found", "message": "Device not found"})
    return dict(row)


@app.get("/api/v1/devices/{device_id}/telemetry/latest")
def latest(device_id: str):
    with connection() as db:
        row = db.execute(
            "SELECT * FROM telemetry WHERE device_id=? ORDER BY timestamp DESC LIMIT 1",
            (device_id,),
        ).fetchone()
    if not row:
        raise HTTPException(404, detail={"code": "reading_not_found", "message": "No telemetry for device"})
    return dict(row)


@app.get("/api/v1/devices/{device_id}/telemetry")
def history(
    device_id: str,
    limit: int = Query(100, ge=1, le=500),
    since: datetime | None = None,
    until: datetime | None = None,
    offset: int = Query(0, ge=0, le=100000),
):
    if since and until and _utc_iso(since) > _utc_iso(until):
        raise HTTPException(400, detail={"code": "invalid_time_range", "message": "since must be earlier than or equal to until"})
    sql = "SELECT * FROM telemetry WHERE device_id=?"
    args: list[Any] = [device_id]
    if since:
        sql += " AND timestamp>=?"
        args.append(_utc_iso(since))
    if until:
        sql += " AND timestamp<=?"
        args.append(_utc_iso(until))
    sql += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
    args.extend([limit + 1, offset])
    with connection() as db:
        rows = db.execute(sql, args).fetchall()
    has_more = len(rows) > limit
    items = [dict(row) for row in reversed(rows[:limit])]
    return {"items": items, "limit": limit, "offset": offset, "has_more": has_more}


@app.get("/api/v1/alerts")
def alerts(limit: int = Query(50, ge=1, le=500), offset: int = Query(0, ge=0, le=100000)):
    with connection() as db:
        rows = db.execute(
            "SELECT * FROM telemetry WHERE alert_status!='normal' ORDER BY timestamp DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
    return {"items": [dict(row) for row in rows], "limit": limit, "offset": offset}


@app.get("/api/v1/analytics/summary")
def summary():
    with connection() as db:
        devices_count = db.execute("SELECT COUNT(DISTINCT device_id) FROM telemetry").fetchone()[0]
        row = db.execute("SELECT AVG(temperature),AVG(humidity),AVG(air_quality),MAX(timestamp) FROM telemetry").fetchone()
        alert_count = db.execute("SELECT COUNT(*) FROM telemetry WHERE alert_status!='normal'").fetchone()[0]
    return {
        "device_count": devices_count,
        "temperature": round(row[0] or 0, 1),
        "humidity": round(row[1] or 0, 1),
        "air_quality": round(row[2] or 0, 1),
        "alert_count": alert_count,
        "updated_at": row[3],
    }


@app.get("/api/v1/analytics/history")
def analytics_history(limit: int = Query(48, ge=1, le=500)):
    return history("home-sensor-01", limit=limit)


class Command(BaseModel):
    command: str = Field(min_length=1, max_length=64)
    parameters: dict[str, Any] = Field(default_factory=dict)


@app.post("/api/v1/devices/{device_id}/commands", status_code=202)
def command(device_id: str, payload: Command):
    if DEMO_MODE:
        return {"accepted": True, "device_id": device_id, "command": payload.command, "mode": "local-demo"}
    raise HTTPException(501, detail={"code": "commands_unavailable", "message": "Configure an authenticated IoT command publisher"})


@app.post("/api/v1/telemetry", status_code=201)
def ingest(reading: Reading, x_ingestion_token: str | None = Header(default=None, alias="X-Ingestion-Token")):
    if not DEMO_MODE:
        if not INGESTION_API_TOKEN:
            raise HTTPException(503, detail={"code": "ingestion_not_configured", "message": "Telemetry ingestion is not configured"})
        if not x_ingestion_token or not hmac.compare_digest(x_ingestion_token, INGESTION_API_TOKEN):
            raise HTTPException(401, detail={"code": "unauthorized", "message": "Invalid ingestion credentials"})

    timestamp = reading.timestamp.astimezone(timezone.utc).isoformat()
    alert_status = (
        "critical" if reading.temperature >= 35 or reading.humidity >= 75
        else "warning" if reading.temperature >= 30 or reading.humidity >= 60
        else "normal"
    )
    with connection() as db:
        cursor = db.execute(
            "INSERT OR IGNORE INTO telemetry VALUES(?,?,?,?,?,?,?)",
            (reading.device_id, timestamp, reading.temperature, reading.humidity, reading.air_quality, reading.status, alert_status),
        )
    stored = cursor.rowcount == 1
    log.info(json.dumps({
        "event": "telemetry_ingested" if stored else "duplicate_telemetry_ignored",
        "device_id": reading.device_id,
        "alert_status": alert_status,
    }))
    return {"stored": stored, "alert_status": alert_status}
