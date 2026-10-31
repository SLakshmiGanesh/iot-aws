"""AWS IoT telemetry rule target. Configure TABLE_NAME and optional thresholds."""
import json, os
from datetime import datetime, timezone
from decimal import Decimal
import boto3
from botocore.exceptions import BotoCoreError, ClientError

TABLE_NAME=os.environ.get("TABLE_NAME")
def _number(value, name, low, high):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not low <= value <= high:
        raise ValueError(f"{name} out of range")
    return Decimal(str(value))
def handler(event, context):
    if not isinstance(event,dict): raise ValueError("event must be an object")
    device=event.get("device_id")
    if not isinstance(device,str) or not 1 <= len(device) <= 64: raise ValueError("invalid device_id")
    timestamp=event.get("timestamp")
    try: parsed=datetime.fromisoformat(timestamp.replace("Z","+00:00")).astimezone(timezone.utc)
    except (ValueError,AttributeError): raise ValueError("invalid timestamp")
    item={"device_id":device,"timestamp":parsed.isoformat().replace("+00:00","Z"),
      "temperature":_number(event.get("temperature"),"temperature",-40,85),
      "humidity":_number(event.get("humidity"),"humidity",0,100),
      "air_quality":int(_number(event.get("air_quality"),"air_quality",0,10000)),
      "status":event.get("status","online")}
    temp_warn=float(os.getenv("TEMP_WARNING","30")); temp_critical=float(os.getenv("TEMP_CRITICAL","35"))
    hum_warn=float(os.getenv("HUMIDITY_WARNING","60")); hum_critical=float(os.getenv("HUMIDITY_CRITICAL","75"))
    item["alert_status"]="critical" if float(item["temperature"])>=temp_critical or float(item["humidity"])>=hum_critical else "warning" if float(item["temperature"])>=temp_warn or float(item["humidity"])>=hum_warn else "normal"
    if not TABLE_NAME: raise RuntimeError("TABLE_NAME is not configured")
    try:
        boto3.resource("dynamodb").Table(TABLE_NAME).put_item(Item=item)
    except (BotoCoreError,ClientError):
        print(json.dumps({"event":"telemetry_write_failed","device_id":device}))
        raise
    print(json.dumps({"event":"telemetry_processed","device_id":device,"alert_status":item["alert_status"]}))
    return {"stored":True,"device_id":device,"alert_status":item["alert_status"]}
