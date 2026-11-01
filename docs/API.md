# API reference

## Local FastAPI mode

OpenAPI UI is available at `/docs` when the local backend is running.

| Method | Route | Behavior |
| --- | --- | --- |
| GET | `/health` | Liveness response |
| GET | `/api/v1/devices` | Device list |
| GET | `/api/v1/devices/{device_id}` | Device summary |
| GET | `/api/v1/devices/{device_id}/telemetry/latest` | Latest device reading |
| GET | `/api/v1/devices/{device_id}/telemetry` | History; supports `limit`, `since`, `until` |
| GET | `/api/v1/alerts` | Recent non-normal readings |
| GET | `/api/v1/analytics/summary` | Summary values |
| GET | `/api/v1/analytics/history` | Demo-device history |
| POST | `/api/v1/telemetry` | Validated local reading ingestion |
| POST | `/api/v1/devices/{device_id}/commands` | Local-demo acknowledgment only; no AWS command is sent |

Timestamps should be timezone-aware ISO-8601 values. Sensor values are bounded by the Pydantic reading schema.

## AWS read API

Terraform creates a public API Gateway HTTP API with dashboard read routes: `GET /health`, `GET /api/v1/devices`, `GET /api/v1/devices/{device_id}`, `GET /api/v1/devices/{device_id}/telemetry`, `GET /api/v1/devices/{device_id}/telemetry/latest`, `GET /api/v1/alerts`, `GET /api/v1/analytics/summary`, and `GET /api/v1/analytics/history`.

Device list, history, and alert routes accept a bounded `limit`; device list and telemetry history return an opaque `next_token` when more results are available. History accepts timezone-aware ISO `since` and `until` values with `since <= until`. Invalid limits or time ranges return HTTP 400. Device routes first check membership in the deployment's configured home.

The API Lambda uses DynamoDB Query/GetItem; there are no write or device-command routes. API Gateway applies throttling. Browser CORS is restricted to the provisioned CloudFront origin, but the API has no user authentication: CORS is not an access-control boundary. The current stack targets one configured home and should not expose confidential readings. The API endpoint is available as Terraform output `api_url`.
