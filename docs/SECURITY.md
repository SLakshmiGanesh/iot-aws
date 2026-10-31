# Security

## Device identity and telemetry
Use a unique AWS IoT certificate per physical device and attach it to a Thing. Attach the Terraform-created IoT policy and set the Thing's `home_id` attribute before connecting. Policy variables scope connect to that Thing and publish to only that Thing's telemetry/status topic path. Provision private keys outside source control; rotate certificates and revoke compromised identities. Firmware must validate the AWS root CA and never disable TLS verification.

## Cloud processing and API
The ingestion Lambda validates required fields and reading ranges, normalizes timestamps, stores history, and conditionally updates latest device state. It logs event names, device IDs, and alert states without logging credential material. Its IAM role can write only to the telemetry and device tables. The dashboard API Lambda has read-only Query/GetItem permissions. The public API Gateway endpoint uses CloudFront-origin CORS and throttling; it contains no write endpoint or command publisher.

## Local development and reporting
Local mode is SQLite-backed and separate from AWS mode. Never present seeded local readings as cloud data. Keep credentials, private keys, certificates, Terraform state, and production data out of source control. Report vulnerabilities privately to the repository owner rather than posting exploit details publicly.
