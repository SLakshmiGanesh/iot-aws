# IAM role policy resources are defined alongside the root Lambda for direct references.
output "module_note" {
  value = "Least-privilege runtime permissions are attached in the root stack."
}
