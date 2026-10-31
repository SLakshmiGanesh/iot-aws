# Lambda resources are defined in the root stack so IoT, table and logging references remain explicit.
output "module_note" { value="See the root Terraform stack for Lambda deployment configuration." }
