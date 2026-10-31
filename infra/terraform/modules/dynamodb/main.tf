variable "table_name" { type=string }
resource "aws_dynamodb_table" "this" {
  name=var.table_name
  billing_mode="PAY_PER_REQUEST"
  hash_key="device_id"
  range_key="timestamp"
  attribute { name="device_id", type="S" }
  attribute { name="timestamp", type="S" }
  server_side_encryption { enabled=true }
  point_in_time_recovery { enabled=true }
}
output "table_arn" { value=aws_dynamodb_table.this.arn }
output "table_name" { value=aws_dynamodb_table.this.name }
