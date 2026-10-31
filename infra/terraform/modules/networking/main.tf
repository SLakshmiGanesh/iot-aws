# ECS/networking module scaffold is intentionally not instantiated by the local-first stack.
output "note" {
  value = "Deploy private subnets, NAT and endpoints according to the selected VPC topology before enabling ECS."
}
