# Cost estimation

This document provides a cost model, not a quoted bill. AWS prices vary by region, usage, account discounts, and time. Use the AWS Pricing Calculator with the target region and workload before deployment.

## Cost drivers

| Service | Main usage driver |
| --- | --- |
| AWS IoT Core | Connected minutes and MQTT message volume |
| Lambda | Invocation count, duration, and allocated memory |
| DynamoDB | Read/write request volume, storage, backups, and point-in-time recovery |
| API Gateway | API request volume |
| CloudFront | Data transfer and request count |
| S3 | Stored dashboard assets and requests |
| CloudWatch | Log ingestion, stored logs, alarms, and metrics |

## Estimate inputs

For a first estimate, record:

- Number of devices.
- Average telemetry interval in seconds.
- Average payload size in bytes.
- Expected dashboard viewers and refresh interval.
- Telemetry retention in days.
- Region and expected monthly data transfer.
- Whether PITR and exported backups are enabled.

Approximate messages per month:

```text
devices × (seconds per month ÷ telemetry interval seconds)
```

Use the message count to estimate IoT ingestion and Lambda invocations. Include status events, retries, API polling, and development/test traffic separately.

## Cost controls

- Keep the default PAY_PER_REQUEST database mode for low or variable demonstration traffic.
- Choose a retention period appropriate to the use case; TTL deletion is asynchronous.
- Keep CloudFront price class and dashboard size modest for a demo.
- Review CloudWatch log retention and alarm count.
- Set AWS Budgets alerts in the account before applying infrastructure.
- Destroy unused development resources after verifying the exact Terraform plan.
- Remember that a deployed CloudFront distribution can continue to incur charges even with little traffic.

The repository does not promise a fixed monthly cost. A real estimate requires workload assumptions and current regional rates.
