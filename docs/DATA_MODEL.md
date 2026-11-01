# Data model

## Telemetry table

Terraform provisions a DynamoDB table with:

- Partition key: `device_id`.
- Sort key: `timestamp` (UTC ISO-8601 string).
- Global secondary index: `alert-status-timestamp-index` with `alert_status` as partition key and `timestamp` as sort key.
- TTL attribute: `expires_at` as Unix epoch seconds.
- Server-side encryption and point-in-time recovery enabled.

Telemetry items also contain `home_id`, `event_id`, temperature, humidity, air quality, status, alert classification, and expiration time. The API filters by configured home. The base table key does not include home, so device identifiers should be globally unique across deployments sharing a table. A future multi-tenant design should use a composite home/device partition key and a home-scoped alert index.

## Device registry table

- Partition key: `home_id`.
- Sort key: `device_id`.
- Latest telemetry fields are conditionally updated only when their timestamp is newer.
- Presence fields include online/offline status and last status update time.

## Timestamp and identity rules

- Device telemetry timestamp is normalized to UTC.
- Events outside the configured replay-age and future-skew window are rejected.
- Device IDs use letters, digits, underscore, or hyphen and are limited to 64 characters.
- Event IDs are stored for investigation. The DynamoDB telemetry primary key currently makes repeated writes to the same device/timestamp conditional and idempotent.

## Local database

The local demo stores telemetry in SQLite with a composite primary key of device ID and timestamp. It is separate from AWS DynamoDB and uses synthetic demo readings when run in local mode.
