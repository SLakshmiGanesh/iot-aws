output "aws_region" {
  value = var.aws_region
}
output "telemetry_table_name" {
  value = aws_dynamodb_table.telemetry.name
}
output "devices_table_name" {
  value = aws_dynamodb_table.devices.name
}
output "lambda_function_name" {
  value = aws_lambda_function.processor.function_name
}
output "api_lambda_function_name" {
  value = aws_lambda_function.api.function_name
}
output "device_status_lambda_name" {
  value = aws_lambda_function.device_status.function_name
}
output "device_status_rule_name" {
  value = aws_iot_topic_rule.device_status.name
}
output "iot_rule_name" {
  value = aws_iot_topic_rule.telemetry.name
}
output "iot_device_policy_name" {
  value = aws_iot_policy.device.name
}
output "dashboard_url" {
  description = "HTTPS CloudFront URL for the static dashboard."
  value       = "https://${aws_cloudfront_distribution.dashboard.domain_name}"
}
output "dashboard_bucket_name" {
  description = "Private S3 bucket that stores the compiled dashboard."
  value       = aws_s3_bucket.dashboard.id
}
output "cloudfront_distribution_id" {
  value = aws_cloudfront_distribution.dashboard.id
}
output "api_url" {
  description = "Public HTTPS API Gateway URL used by the dashboard."
  value       = aws_apigatewayv2_api.dashboard.api_endpoint
}
