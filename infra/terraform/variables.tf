variable "aws_region" { type = string, default = "us-east-1" }
variable "project_name" { type = string, default = "home-monitor" }
variable "environment" { type = string, default = "dev" }
variable "telemetry_table_name" { type = string, default = "home-telemetry" }
variable "lambda_zip_path" { type = string, default = "../../cloud/lambda/deployment.zip" }
