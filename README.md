# Smart Home IoT Monitoring Platform

A full-stack smart home monitoring project that collects environmental readings from ESP32 devices, stores telemetry, detects threshold alerts, and presents device health and history in a web dashboard.

The project supports two ways to run:

- **Local demo:** start the application with Docker Compose and explore sample telemetry without AWS hardware or credentials.
- **AWS deployment:** use Terraform to provision the cloud pipeline and host the dashboard through CloudFront.

## What the system does

An ESP32 reads temperature, humidity, and air-quality sensor values and publishes them over MQTT. In AWS mode, AWS IoT Core receives the messages and routes them to Lambda for validation and processing. The processor stores readings and device status in DynamoDB. A read-only HTTP API serves dashboard data, and the React dashboard displays recent values, device availability, history, and threshold alerts.

The local demo follows the same general user journey with a FastAPI service, SQLite storage, and a telemetry simulator. It is intended for development and demonstration; it does not connect to AWS.

## Main features

- **Device telemetry:** ESP32 firmware publishes timestamped temperature, humidity, and air-quality readings using MQTT over TLS.
- **Device presence:** retained MQTT status messages report when a device comes online or goes offline.
- **Telemetry processing:** AWS Lambda validates incoming messages, persists telemetry, updates the device's latest state, and marks threshold alerts.
- **History and alert queries:** DynamoDB stores readings by device and time, with an alert index and configurable retention.
- **Monitoring dashboard:** React and TypeScript UI provides device selection, summary metrics, history charts, alert listings, and periodic refresh.
- **Cloud delivery:** private S3 website assets are served through CloudFront; API Gateway provides the dashboard's read-only data API.
- **Local development:** FastAPI, SQLite, sample data, a simulator, Docker Compose, and automated checks make it possible to run the demo without cloud resources.

## Architecture

### AWS mode

```text
ESP32 sensors
    │ MQTT over TLS
    ▼
AWS IoT Core
    │ IoT rules
    ▼
Lambda processors ───────► DynamoDB telemetry and device registry
                                  ▲
                                  │ read-only queries
                                  │
CloudFront ──► React dashboard ──► API Gateway ──► API Lambda
    │
    └── serves static files from a private S3 bucket
```

CloudWatch tracks Lambda errors/throttles and alerts when the encrypted SQS failure queue receives an event. Lambda async failures retry up to the configured limit before entering that queue. The API is public and read-only; CORS is restricted to the dashboard origin, but CORS is not authentication. The current stack is for one configured home and must not serve confidential data.

### Local demo

```text
Telemetry simulator ──► FastAPI service ──► SQLite
                              ▲
                              │
                        React dashboard
```

## Run locally

Requirements: Docker Desktop with Docker Compose.

From the repository root, run:

```sh
docker compose up --build
```

Then open:

- Dashboard: http://localhost:5173
- API documentation: http://localhost:8000/docs

The local application uses SQLite and demo readings. It does not create AWS resources or require AWS credentials.

## Deploy to AWS

See [AWS deployment instructions](docs/AWS_DEPLOYMENT.md) for prerequisites and commands.

The Terraform configuration provisions the IoT telemetry pipeline, DynamoDB tables, Lambda functions, read-only API Gateway, CloudFront distribution, and private S3 hosting. The deployment guide builds the Lambda package, reviews the Terraform plan, applies infrastructure, then builds and uploads the dashboard using the generated API URL.

**This repository has not been deployed to AWS by this project.** A successful deployment requires an operator-authenticated AWS session and an explicit review of the Terraform plan. AWS usage may incur charges.

The infrastructure does not provision IoT certificates or register physical devices. Before connecting firmware, create an AWS IoT Thing and certificate, set the Thing's `home_id` attribute, and attach the generated IoT policy. Keep AWS credentials, certificates, and private keys out of the repository.

## Repository layout

| Path | Purpose |
| --- | --- |
| `backend/` | FastAPI local demo API, SQLite storage, and backend tests |
| `frontend/` | React and TypeScript monitoring dashboard |
| `firmware/` | ESP32 firmware and Wokwi sensor layout |
| `cloud/lambda/` | AWS telemetry processor, API handler, and package builder |
| `infra/terraform/` | AWS resource definitions and deployment configuration |
| `simulator/` | Local telemetry publisher for the demo |
| `docs/` | Deployment, architecture, API, security, operations, data model, testing, and cost guides |

## Checks

Backend tests:

```sh
cd backend
pip install -r requirements.txt pytest httpx
$env:PYTHONPATH="."
pytest
```

Frontend production build:

```sh
cd frontend
npm install
npm run build
```

Lambda and Terraform checks are also configured in GitHub Actions where the required tools are available.

## Engineering guides\n\n- [Architecture](docs/ARCHITECTURE.md) · [API](docs/API.md) · [Development](docs/DEVELOPMENT.md)\n- [Security](docs/SECURITY.md) · [Threat model](docs/THREAT_MODEL.md) · [Operations](docs/OPERATIONS.md)\n- [Data model](docs/DATA_MODEL.md) · [Testing](docs/TESTING.md) · [Cost estimation](docs/COST_ESTIMATION.md)\n\n## Scope and limitations

- The AWS dashboard API is read-only; device command publishing is not implemented.
- ECS/Fargate hosting is not part of this project.
- Wokwi can simulate the firmware and wiring, but it does not provision AWS IoT certificates.
- The AWS API has no user authentication; home scoping does not make the public endpoint private.
- The telemetry table is keyed by device and timestamp; device identifiers must be unique wherever a table is shared.
- AWS alarms do not currently send notifications, and certificate rotation remains an operator procedure.
- Alert thresholds are demonstration settings and are not health or safety guidance.
