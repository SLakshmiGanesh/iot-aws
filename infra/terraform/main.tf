resource "aws_dynamodb_table" "telemetry" {
  name         = var.telemetry_table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "device_id"
  range_key    = "timestamp"

  attribute {
    name = "device_id"
    type = "S"
  }
  attribute {
    name = "timestamp"
    type = "S"
  }
  server_side_encryption {
    enabled = true
  }
  point_in_time_recovery {
    enabled = true
  }
}

resource "aws_iam_role" "lambda" {
  name = "${var.project_name}-${var.environment}-processor"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${var.project_name}-${var.environment}-processor"
  retention_in_days = 30
}

resource "aws_iam_role_policy" "lambda" {
  name = "${var.project_name}-telemetry-writer"
  role = aws_iam_role.lambda.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["dynamodb:PutItem"]
        Resource = aws_dynamodb_table.telemetry.arn
      },
      {
        Effect   = "Allow"
        Action   = ["logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "${aws_cloudwatch_log_group.lambda.arn}:*"
      }
    ]
  })
}

resource "aws_lambda_function" "processor" {
  function_name    = "${var.project_name}-${var.environment}-processor"
  role             = aws_iam_role.lambda.arn
  runtime          = "python3.12"
  handler          = "handler.handler"
  filename         = var.lambda_zip_path
  source_code_hash = filebase64sha256(var.lambda_zip_path)
  timeout          = 10
  memory_size      = 256
  depends_on       = [aws_iam_role_policy.lambda, aws_cloudwatch_log_group.lambda]

  environment {
    variables = {
      TABLE_NAME        = aws_dynamodb_table.telemetry.name
      TEMP_WARNING      = tostring(var.temperature_warning)
      TEMP_CRITICAL     = tostring(var.temperature_critical)
      HUMIDITY_WARNING  = tostring(var.humidity_warning)
      HUMIDITY_CRITICAL = tostring(var.humidity_critical)
    }
  }
}

resource "aws_iot_topic_rule" "telemetry" {
  name        = "${replace(var.project_name, "-", "_")}_${var.environment}_telemetry_to_lambda"
  enabled     = true
  sql         = "SELECT * FROM 'home/+/devices/+/telemetry'"
  sql_version = "2016-03-23"
  lambda {
    function_arn = aws_lambda_function.processor.arn
  }
}

resource "aws_lambda_permission" "iot" {
  statement_id  = "AllowIoTRule"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.processor.function_name
  principal     = "iot.amazonaws.com"
  source_arn    = aws_iot_topic_rule.telemetry.arn
}
