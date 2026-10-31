# API reference

## Local FastAPI mode

OpenAPI UI is available at `/docs` when the local backend is running.

- `GET /health`
- `GET /api/v1/devices`
- `GET /api/v1/devices/{device_id}`
- `GET /api/v1/devices/{device_id}/telemetry?limit=100&since=&until=`
- `GET /api/v1/devices/{device_id}/telemetry/latest`
- `GET /api/v1/alerts`
- `GET /api/v1/analytics/summary`
- `GET /api/v1/analytics/history`
- `POST /api/v1/telemetry` accepts validated local readings
- `POST /api/v1/devices/{device_id}/commands` is a local-demo acknowledgment only

## AWS read API

Terraform creates a public API Gateway HTTP API with the same dashboard read routes: `GET /health`, `GET /api/v1/devices`, `GET /api/v1/devices/{device_id}`, `GET /api/v1/devices/{device_id}/telemetry`, `GET /api/v1/devices/{device_id}/telemetry/latest`, `GET /api/v1/alerts`, `GET /api/v1/analytics/summary`, and `GET /api/v1/analytics/history`.

The API uses a Lambda reader and DynamoDB Query/GetItem operations; it has no write or device-command route. Query limits are capped, API Gateway throttling is configured in Terraform, and browser CORS permits only the provisioned CloudFront distribution origin. The API endpoint is available as Terraform output `api_url`.
