# Smart Home IoT Environmental Monitoring Platform

A local-first and AWS-deployable portfolio platform for collecting ESP32 environmental readings, processing alerts, querying device history, and monitoring the home from a responsive dashboard.

## Architecture and capabilities

- ESP32 Arduino firmware and Wokwi sensor layout for DHT22 temperature/humidity and analog air quality.
- MQTT telemetry over TLS with QoS 1, Thing-scoped AWS IoT policy, separate telemetry/presence IoT Rules, validating Lambdas, and retained online/offline state.
- DynamoDB time-series telemetry table with device/time keys, alert-status GSI and 90-day configurable TTL; separate per-home registry with monotonic latest-reading and online/offline state.
- Read-only API Gateway HTTP API backed by a least-privilege Lambda reader, CORS restricted to the CloudFront origin, and request throttling.
- React + TypeScript dashboard with device selection, telemetry history, summary metrics, recent threshold alerts, and live refresh.
- Private S3 origin behind CloudFront; API Gateway is rate-limited, Lambda failures/throttles raise CloudWatch alarms, and Terraform emits API and website URLs.
- Local SQLite demo, synthetic publisher, Docker Compose, tests, and GitHub Actions.

## Run locally

Install Docker Desktop with Compose, then run:

```sh
docker compose up --build
```

Dashboard: http://localhost:5173. API docs: http://localhost:8000/docs. Local mode seeds demo readings in SQLite and does not connect to AWS.

## Deploy to AWS

Follow [AWS deployment](docs/AWS_DEPLOYMENT.md). Terraform creates the AWS IoT telemetry pipeline, DynamoDB tables, Lambda functions, read-only API Gateway, CloudFront, and private S3 hosting. The guide builds the Lambda package, reviews the Terraform plan, applies infrastructure explicitly, then builds/uploads the dashboard with the generated API URL.

No AWS resources have been deployed from this repository. The project does not provision ECS/Fargate or IoT certificates. Provision a Thing and certificate, set its `home_id` Thing attribute, and attach the generated IoT policy before connecting firmware. Never commit credentials or private device keys.

## Repository map

- `backend/`: FastAPI/SQLite local mode and tests.
- `frontend/`: React monitoring dashboard.
- `firmware/`: ESP32 firmware and Wokwi wiring.
- `cloud/lambda/`: telemetry processor, API handler, and package builder.
- `infra/terraform/`: AWS resources and environment configuration.
- `simulator/`: local telemetry publisher.
- `docs/`: setup, architecture, API, and security.

## Tests and current limits

Backend: `cd backend && pip install -r requirements.txt pytest httpx && PYTHONPATH=. pytest`. Frontend: `cd frontend && npm install && npm run build`. Lambda and Terraform tests are included in repository CI where supported.

Cloud mode depends on an operator-authenticated AWS profile and a reviewed plan/apply. The CloudFront dashboard reads telemetry through the public, read-only API Gateway endpoint. Command publishing and ECS hosting are not implemented. Wokwi cannot provision real AWS IoT certificates. Thresholds are configurable demonstration thresholds, not health or safety standards.

Reference architecture inspiration: https://github.com/khaoula-ghz/smart-home-iot-monitoring (independently implemented).
