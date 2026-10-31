output "telemetry_table_name" { value=aws_dynamodb_table.telemetry.name }
output "lambda_function_name" { value=aws_lambda_function.processor.function_name }
