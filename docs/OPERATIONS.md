# Operations guide

## Runtime signals

The AWS stack creates CloudWatch log groups for the processor, status handler, and read API with configured retention, plus Lambda error and throttle alarms. These alarms currently have no SNS notification target, so operators must inspect CloudWatch or add an approved notification channel.

The local demo exposes `GET /health`. AWS exposes `GET /health` through API Gateway. A successful health response only confirms that the handler is reachable; it does not prove DynamoDB, IoT ingestion, or device connectivity is healthy.

## Triage

### No new telemetry
1. Check device power, Wi-Fi, clock synchronization, and serial logs.
2. Confirm the Thing certificate is active and attached to the expected Thing.
3. Check the Thing's `home_id` attribute and attached policy.
4. Confirm the device publishes under `home/{home_id}/devices/{thing_name}/telemetry`.
5. Inspect the IoT rule, processor Lambda logs, and Lambda error metrics.
6. Check that table names and configured `HOME_ID` match the deployment.

### Device appears offline
1. Check the retained status message and Last Will topic.
2. Inspect the device-status IoT rule and Lambda logs.
3. Confirm the registry record exists; status events received before first telemetry are ignored.

### Dashboard is empty or unavailable
1. Check the CloudFront distribution and confirm dashboard assets were uploaded to its private S3 origin.
2. Check browser network errors, configured API URL, API Gateway throttling, and CORS origin.
3. Call `/health`, then the device-list endpoint.
4. Check API Lambda logs and DynamoDB query errors.

## Failure queue

The encrypted SQS failure queue retains failed asynchronous Lambda events for up to 14 days after bounded retries. When its CloudWatch alarm fires, inspect the queue and corresponding Lambda logs, identify the fault, and verify whether telemetry was partially written before deciding whether to redrive or discard a message. Do not replay messages until the cause is fixed; the processor's device/timestamp conditional write makes repeated deliveries safe for the same key. Automated redrive tooling is not configured.

## Recovery

- Rebuild the Lambda package from source and redeploy through a reviewed Terraform plan.
- Restore DynamoDB data using point-in-time recovery only after reviewing the recovery point and blast radius.
- Revoke and replace a compromised device certificate, then update the device securely.
- For deployment failure, preserve the Terraform plan and state; do not delete resources as a troubleshooting shortcut.

## Operational gaps

On-call notifications, certificate rotation automation, backup export, and restore drills are not currently configured. Add these before relying on the platform for critical monitoring.
