output "aws_region" {
  value = var.aws_region
}
output "telemetry_table_name" {
  value = aws_dynamodb_table.telemetry.name
}
output "lambda_function_name" {
  value = aws_lambda_function.processor.function_name
}
output "iot_rule_name" {
  value = aws_iot_topic_rule.telemetry.name
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
