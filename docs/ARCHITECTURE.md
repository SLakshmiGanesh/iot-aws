# Architecture
```mermaid
flowchart LR
  ESP[ESP32 / Wokwi sensors] -->|MQTT TLS QoS 1| IOT[AWS IoT Core]
  IOT --> RULE[IoT Rules]
  RULE --> L[Lambda validation and thresholds]
  L --> D[(DynamoDB)]
  L --> CW[CloudWatch logs]
  D --> API[FastAPI]
  API --> UI[React dashboard]
  SIM[Local demo readings] --> DB[(SQLite)]
  DB --> API
```
The local dashboard uses SQLite demo data. AWS-mode data access remains an integration point; the Lambda and Terraform establish a cloud ingestion foundation. Table keys are device_id and ISO-8601 UTC timestamp for per-device range queries.
