"""Send synthetic readings to the local REST API (no AWS access)."""
import json, os, random, time
from datetime import datetime, timezone
from urllib.request import Request, urlopen
API=os.getenv("API_URL","http://localhost:8000")
DEVICE=os.getenv("DEVICE_ID","home-sensor-01")
while True:
    body=json.dumps({"device_id":DEVICE,"timestamp":datetime.now(timezone.utc).isoformat(),"temperature":round(random.uniform(21,28),1),"humidity":round(random.uniform(40,65),1),"air_quality":random.randint(50,150),"status":"online"}).encode()
    req=Request(API+"/api/v1/telemetry",data=body,headers={"Content-Type":"application/json"},method="POST")
    with urlopen(req,timeout=5) as response: print(response.read().decode())
    time.sleep(int(os.getenv("INTERVAL_SECONDS","15")))
