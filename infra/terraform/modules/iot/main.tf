variable "lambda_arn" {
  type = string
}

resource "aws_iot_topic_rule" "telemetry" {
  name        = "home_telemetry_to_lambda"
  enabled     = true
  sql         = "SELECT * FROM 'home/+/devices/+/telemetry'"
  sql_version = "2016-03-23"

  lambda {
    function_arn = var.lambda_arn
  }
}

resource "aws_lambda_permission" "iot" {
  statement_id  = "AllowIoTRule"
  action        = "lambda:InvokeFunction"
  function_name = var.lambda_arn
  principal     = "iot.amazonaws.com"
  source_arn    = aws_iot_topic_rule.telemetry.arn
}
