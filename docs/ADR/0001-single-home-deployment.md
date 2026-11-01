# ADR 0001: Scope each deployment to one configured home

- Status: Accepted for the current demonstration architecture
- Date: 2026-11-01

## Context

The initial AWS deployment uses one configured `HOME_ID` and a public read-only dashboard API. The device registry is keyed by home and device, but the telemetry table is partitioned by device identifier. A general multi-tenant service would require stronger identity-aware authorization and home-scoped storage/index keys.

## Decision

Treat one Terraform deployment as one configured home. Pass the home and device identity from the MQTT topic into the ingestion Lambda, reject mismatched home/device fields, store the home ID on each telemetry item, and filter dashboard telemetry and alerts to the configured home.

## Consequences

This reduces accidental cross-home query exposure within the configured stack. It does not authenticate dashboard viewers, so the AWS API remains public and must not contain data that requires user-level confidentiality. Device IDs should be globally unique if telemetry tables are shared. A future multi-tenant deployment requires a revised telemetry key/index design, authenticated API access, and migration planning.
