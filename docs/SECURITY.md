# Security

## Device identity and telemetry

Use a unique AWS IoT certificate per physical device and attach it to a Thing. Attach the Terraform-created policy and set the Thing's `home_id` attribute before connecting. Policy variables scope connect to the Thing and publish to only that Thing's telemetry/status topic paths. Provision private keys outside source control; rotate certificates and revoke compromised identities. Firmware validates the configured AWS root CA and must never disable TLS verification.

The IoT rules enrich events with home and device identity from the topic. The processor validates those fields, identifier format, sensor ranges, and timestamp replay bounds. It conditionally writes telemetry and advances device latest state only for newer timestamps. Lambda asynchronous invocations retry a bounded number of times and send failures to an encrypted SQS queue.

## API and local ingestion

The AWS API is public and read-only. It is rate-limited and filters data to the stack's configured home. CORS permits only the CloudFront origin, but CORS is not authentication: anyone can call the endpoint outside a browser. Use only with data intended to be public. User authentication and authorization are not implemented.

The local FastAPI telemetry write route is open only in local demo mode. When the backend runs with a non-local `APP_MODE`, configure `INGESTION_API_TOKEN` through a secret manager or protected runtime environment. Send it as `X-Ingestion-Token`; never commit the token. Prefer a device-authenticated ingress path for real deployments rather than distributing one shared token to a fleet.

## Credentials and operations

Never paste AWS keys, certificates, private keys, tokens, or Terraform state into chat or commit them. Use short-lived AWS identities. If a credential is exposed, revoke it and investigate account activity.

CloudWatch alarms cover Lambda errors, throttles, and failure-queue depth. They currently have no notification target, so operators must check them manually or configure an approved SNS destination. Certificate rotation and Thing provisioning are currently operator procedures.

## Local development and reporting

Local SQLite is separate from AWS mode. Never present seeded local readings as cloud data. Keep production data and credentials out of source control. Report vulnerabilities privately to the repository owner rather than posting exploit details publicly.
