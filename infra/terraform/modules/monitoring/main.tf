variable "lambda_function_name" {
  type = string
}

resource "aws_cloudwatch_metric_alarm" "errors" {
  alarm_name          = "${var.lambda_function_name}-errors"
  namespace           = "AWS/Lambda"
  metric_name         = "Errors"
  dimensions          = { FunctionName = var.lambda_function_name }
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
}
