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
