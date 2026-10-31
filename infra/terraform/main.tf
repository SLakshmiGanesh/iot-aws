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
  attribute {
    name = "alert_status"
    type = "S"
  }
  global_secondary_index {
    name            = "alert-status-timestamp-index"
    hash_key        = "alert_status"
    range_key       = "timestamp"
    projection_type = "ALL"
  }
  server_side_encryption {
    enabled = true
  }
  point_in_time_recovery {
    enabled = true
  }
}

resource "aws_dynamodb_table" "devices" {
  name         = "${var.project_name}-${var.environment}-devices"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "home_id"
  range_key    = "device_id"

  attribute {
    name = "home_id"
    type = "S"
  }
  attribute {
    name = "device_id"
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
  name = "${var.project_name}-${var.environment}-telemetry-writer"
  role = aws_iam_role.lambda.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["dynamodb:PutItem"]
        Resource = [aws_dynamodb_table.telemetry.arn, aws_dynamodb_table.devices.arn]
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
      TABLE_NAME         = aws_dynamodb_table.telemetry.name
      DEVICES_TABLE_NAME = aws_dynamodb_table.devices.name
      HOME_ID            = var.home_id
      TEMP_WARNING       = tostring(var.temperature_warning)
      TEMP_CRITICAL      = tostring(var.temperature_critical)
      HUMIDITY_WARNING   = tostring(var.humidity_warning)
      HUMIDITY_CRITICAL  = tostring(var.humidity_critical)
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

resource "aws_iam_role" "api" {
  name = "${var.project_name}-${var.environment}-read-api"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_cloudwatch_log_group" "api" {
  name              = "/aws/lambda/${var.project_name}-${var.environment}-read-api"
  retention_in_days = 30
}

resource "aws_iam_role_policy" "api" {
  name = "${var.project_name}-${var.environment}-read-only"
  role = aws_iam_role.api.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["dynamodb:Query", "dynamodb:GetItem"]
        Resource = [
          aws_dynamodb_table.telemetry.arn,
          "${aws_dynamodb_table.telemetry.arn}/index/*",
          aws_dynamodb_table.devices.arn
        ]
      },
      {
        Effect   = "Allow"
        Action   = ["logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "${aws_cloudwatch_log_group.api.arn}:*"
      }
    ]
  })
}

resource "aws_lambda_function" "api" {
  function_name    = "${var.project_name}-${var.environment}-read-api"
  role             = aws_iam_role.api.arn
  runtime          = "python3.12"
  handler          = "api_handler.handler"
  filename         = var.lambda_zip_path
  source_code_hash = filebase64sha256(var.lambda_zip_path)
  timeout          = 10
  memory_size      = 256
  depends_on       = [aws_iam_role_policy.api, aws_cloudwatch_log_group.api]

  environment {
    variables = {
      TABLE_NAME         = aws_dynamodb_table.telemetry.name
      DEVICES_TABLE_NAME = aws_dynamodb_table.devices.name
      HOME_ID            = var.home_id
    }
  }
}

resource "aws_apigatewayv2_api" "dashboard" {
  name          = "${var.project_name}-${var.environment}-dashboard-api"
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins = ["https://${aws_cloudfront_distribution.dashboard.domain_name}"]
    allow_methods = ["GET", "OPTIONS"]
    allow_headers = ["content-type"]
    max_age       = 3600
  }
}

resource "aws_apigatewayv2_integration" "dashboard" {
  api_id                 = aws_apigatewayv2_api.dashboard.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.api.invoke_arn
  integration_method     = "POST"
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "dashboard" {
  api_id    = aws_apigatewayv2_api.dashboard.id
  route_key = "$default"
  target    = "integrations/${aws_apigatewayv2_integration.dashboard.id}"
}

resource "aws_apigatewayv2_stage" "dashboard" {
  api_id      = aws_apigatewayv2_api.dashboard.id
  name        = "$default"
  auto_deploy = true
}

resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowHttpApiInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.dashboard.execution_arn}/*/*"
}

resource "aws_iot_policy" "device" {
  name = "${var.project_name}-${var.environment}-device-policy"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["iot:Connect"]
        Resource = "arn:aws:iot:${var.aws_region}:${data.aws_caller_identity.current.account_id}:client/$${iot:Connection.Thing.ThingName}"
      },
      {
        Effect   = "Allow"
        Action   = ["iot:Publish"]
        Resource = [
          "arn:aws:iot:${var.aws_region}:${data.aws_caller_identity.current.account_id}:topic/home/$${iot:Connection.Thing.Attributes[home_id]}/devices/$${iot:Connection.Thing.ThingName}/telemetry",
          "arn:aws:iot:${var.aws_region}:${data.aws_caller_identity.current.account_id}:topic/home/$${iot:Connection.Thing.Attributes[home_id]}/devices/$${iot:Connection.Thing.ThingName}/status"
        ]
      }
    ]
  })
}
