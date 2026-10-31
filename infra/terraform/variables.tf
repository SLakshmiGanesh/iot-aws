variable "aws_region" {
  description = "AWS region for the telemetry stack."
  type        = string
  default     = "us-east-1"
}
variable "project_name" {
  description = "Short prefix used for resource names."
  type        = string
  default     = "home-monitor"
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,24}$", var.project_name))
    error_message = "project_name must be 3-25 lowercase letters, digits, or hyphens and start with a letter."
  }
}
variable "environment" {
  description = "Deployment environment label."
  type        = string
  default     = "dev"
}
variable "telemetry_table_name" {
  description = "DynamoDB table for device telemetry."
  type        = string
  default     = "home-telemetry"
}
variable "lambda_zip_path" {
  description = "Path to the packaged Lambda zip, relative to this Terraform root."
  type        = string
  default     = "../../cloud/lambda/deployment.zip"
}
variable "temperature_warning" {
  type    = number
  default = 30
}
variable "temperature_critical" {
  type    = number
  default = 35
}
variable "humidity_warning" {
  type    = number
  default = 60
}
variable "humidity_critical" {
  type    = number
  default = 75
}
