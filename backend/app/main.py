from __future__ import annotations
import json, logging, os, sqlite3
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field

DB_PATH = Path(os.getenv("DATABASE_PATH", "/data/telemetry.db"))
DEMO_MODE = os.getenv("APP_MODE", "local") == "local"
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(message)s")
log = logging.getLogger("iot_api")

class Reading(BaseModel):
    model_config = ConfigDict(extra="forbid")
    device_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    timestamp: datetime
    temperature: float = Field(ge=-40, le=85)
    humidity: float = Field(ge=0, le=100)
    air_quality: int = Field(ge=0, le=10000)
    status: str = "online"

def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("""CREATE TABLE IF NOT EXISTS telemetry (
      device_id TEXT NOT NULL, timestamp TEXT NOT NULL, temperature REAL NOT NULL,
      humidity REAL NOT NULL, air_quality INTEGER NOT NULL, status TEXT NOT NULL,
      alert_status TEXT NOT NULL, PRIMARY KEY(device_id, timestamp))""")
    return db

def seed():
    with connect() as db:
        if db.execute("SELECT COUNT(*) FROM telemetry").fetchone()[0]: return
        now = datetime.now(timezone.utc)
        for idx in range(48):
            t = now - timedelta(minutes=idx * 15)
            db.execute("INSERT INTO telemetry VALUES(?,?,?,?,?,?,?)",
                ("home-sensor-01", t.isoformat(), round(23 + 2 * __import__("math").sin(idx/5), 1),
                 round(47 + 8 * __import__("math").sin(idx/7), 1), 85 + idx % 24, "online", "normal"))
        db.commit()

@asynccontextmanager
async def lifespan(app: FastAPI):
    if DEMO_MODE: seed()
    yield

app = FastAPI(title="Home Environmental Monitor API", version="1.0.0", lifespan=lifespan)
origins = [x.strip() for x in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET","POST"], allow_headers=["*"])

@app.get("/health")
def health():
    return {"status":"ok", "mode":"local-demo" if DEMO_MODE else "configured"}

@app.get("/api/v1/devices")
def devices():
    with connect() as db:
        rows = db.execute("SELECT device_id, MAX(timestamp) latest, COUNT(*) reading_count FROM telemetry GROUP BY device_id").fetchall()
    return {"items":[dict(r) for r in rows], "total":len(rows)}

@app.get("/api/v1/devices/{device_id}")
def device(device_id: str):
    with connect() as db:
        row=db.execute("SELECT device_id, MAX(timestamp) latest, COUNT(*) reading_count FROM telemetry WHERE device_id=? GROUP BY device_id",(device_id,)).fetchone()
    if not row: raise HTTPException(404, detail={"code":"device_not_found","message":"Device not found"})
    return dict(row)

@app.get("/api/v1/devices/{device_id}/telemetry/latest")
def latest(device_id: str):
    with connect() as db: row=db.execute("SELECT * FROM telemetry WHERE device_id=? ORDER BY timestamp DESC LIMIT 1",(device_id,)).fetchone()
    if not row: raise HTTPException(404, detail={"code":"reading_not_found","message":"No telemetry for device"})
    return dict(row)

@app.get("/api/v1/devices/{device_id}/telemetry")
def history(device_id: str, limit: int=Query(100,ge=1,le=500), since: datetime|None=None, until: datetime|None=None):
    sql="SELECT * FROM telemetry WHERE device_id=?"; args: list[Any]=[device_id]
    if since: sql+=" AND timestamp>=?"; args.append(since.isoformat())
    if until: sql+=" AND timestamp<=?"; args.append(until.isoformat())
    sql+=" ORDER BY timestamp DESC LIMIT ?"; args.append(limit)
    with connect() as db: rows=db.execute(sql,args).fetchall()
    return {"items":[dict(r) for r in reversed(rows)],"limit":limit}

@app.get("/api/v1/alerts")
def alerts(limit: int=Query(50,ge=1,le=500)):
    with connect() as db: rows=db.execute("SELECT * FROM telemetry WHERE alert_status!='normal' ORDER BY timestamp DESC LIMIT ?",(limit,)).fetchall()
    return {"items":[dict(r) for r in rows]}

@app.get("/api/v1/analytics/summary")
def summary():
    with connect() as db:
        devices=db.execute("SELECT COUNT(DISTINCT device_id) FROM telemetry").fetchone()[0]
        row=db.execute("SELECT AVG(temperature),AVG(humidity),AVG(air_quality),MAX(timestamp) FROM telemetry").fetchone()
        alerts=db.execute("SELECT COUNT(*) FROM telemetry WHERE alert_status!='normal'").fetchone()[0]
    return {"device_count":devices,"temperature":round(row[0] or 0,1),"humidity":round(row[1] or 0,1),"air_quality":round(row[2] or 0,1),"alert_count":alerts,"updated_at":row[3]}

@app.get("/api/v1/analytics/history")
def analytics_history(limit: int=Query(48,ge=1,le=500)):
    return history("home-sensor-01",limit)

class Command(BaseModel):
    command: str = Field(min_length=1,max_length=64)
    parameters: dict[str,Any] = Field(default_factory=dict)

@app.post("/api/v1/devices/{device_id}/commands",status_code=202)
def command(device_id: str, payload: Command):
    if DEMO_MODE: return {"accepted":True,"device_id":device_id,"command":payload.command,"mode":"local-demo"}
    raise HTTPException(501,detail={"code":"commands_unavailable","message":"Configure an authenticated IoT command publisher"})

@app.post("/api/v1/telemetry", status_code=201)
def ingest(reading: Reading):
    level = "critical" if reading.temperature > 35 or reading.humidity > 75 else "warning" if reading.temperature > 30 or reading.humidity > 60 else "normal"
    with connect() as db:
        db.execute("INSERT OR REPLACE INTO telemetry VALUES(?,?,?,?,?,?,?)", (reading.device_id,reading.timestamp.astimezone(timezone.utc).isoformat(),reading.temperature,reading.humidity,reading.air_quality,reading.status,level))
        db.commit()
    log.info(json.dumps({"event":"telemetry_stored","device_id":reading.device_id,"alert_status":level}))
    return {"stored":True,"alert_status":level}
