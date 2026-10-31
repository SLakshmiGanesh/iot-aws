# ECS Fargate is not enabled by default; the API can run locally or be containerized for a separately reviewed deployment.
output "note" { value="ECS service deployment requires VPC, ALB, image and task secret configuration." }
