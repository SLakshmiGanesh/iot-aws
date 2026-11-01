# Threat model

## Scope

This model covers the local demo and the AWS IoT telemetry path through the dashboard. The system handles environmental readings, device identifiers, device connectivity state, and AWS resource metadata. It does not currently implement user accounts, tenant management, device commands in AWS, or a certificate lifecycle service.

## Assets

- Device private keys and certificates.
- AWS role credentials and Terraform state.
- Telemetry history and device presence.
- IoT policy and topic configuration.
- Dashboard/API availability and integrity.

## Trust boundaries

1. ESP32 firmware and physical environment.
2. Public network between device and AWS IoT Core.
3. AWS IoT rule execution and Lambda processing.
4. DynamoDB storage.
5. Public API Gateway endpoint and browser clients.
6. Local developer machine and demo database.

## Main threats and controls

| Threat | Current controls | Remaining work |
| --- | --- | --- |
| Device impersonation | Per-device X.509 identity is documented; IoT policy scopes connect/publish to Thing name and home topic | Secure provisioning and rotation automation are manual |
| Eavesdropping or broker impersonation | Firmware uses TLS and validates the configured AWS root CA | Validate real device provisioning end-to-end |
| Unauthorized telemetry topic publish | IoT policy limits publishing to telemetry/status topics for the Thing | Test policy behavior against a real IoT account |
| Malformed or extreme readings | Lambda validates identifier, sensor ranges, timestamp shape, configured home and topic identity | Add rate/anomaly detection and more property tests |
| Duplicate or replayed readings | Conditional DynamoDB write prevents replacing an existing device/timestamp key; bounded event timestamp age; latest state conditional update | Add durable event-id deduplication independent of timestamp |
| Cross-home data exposure | API reads are constrained to configured home and telemetry filters use `home_id` | API is unauthenticated and is intended for a single configured home; do not place sensitive/private data behind it |
| Public API abuse | API Gateway throttling and response-only routes | Add authentication/authorization and abuse monitoring before shared use |
| Credential leakage | Example configs use placeholders; docs prohibit committing credentials | Add automated secret scanning and rotate any exposed credentials |
| Data loss or service failure | DynamoDB PITR and TTL; Lambda errors propagate for retry | Configure a dead-letter path and recovery alarm; test restore procedure |
| Supply-chain vulnerability | Existing workflows run builds/tests | Add pinned actions, dependency review, SBOM, and vulnerability scans |

## Security assumptions

- Each physical device gets a unique Thing and certificate.
- Device credentials are installed through a trusted out-of-band process.
- AWS accounts and developer credentials are not shared.
- Local demo data is synthetic and does not represent AWS state.
- The public dashboard/API contains only data the operator intends to make public.

## Response priorities

1. Revoke a compromised device certificate or AWS identity immediately.
2. Review AWS IoT, CloudTrail, Lambda, API Gateway, and billing activity.
3. Rotate credentials outside source control and redeploy the affected device/configuration.
4. Preserve relevant logs and telemetry for investigation.
5. Record remediation and update this model when trust boundaries change.
