# AWS deployment

This is a deployable ingestion foundation for AWS IoT Core telemetry routing, Lambda processing, DynamoDB storage, IAM, and CloudWatch logs. **No AWS resources have been deployed from this repository.** ECS/Fargate and API read integration are not included in this stack.

## Prerequisites

- An AWS account and an IAM Identity Center/assumed role or other short-lived credentials with permissions for the resources in the Terraform plan.
- AWS CLI, Terraform >= 1.6, and Python 3.
- Use a dedicated dev account or region first. Do not paste AWS access keys into chat or commit them to the repo.

Authenticate locally with your organization's approved method (for example `aws sso login --profile iot-dev`) and verify the identity with `aws sts get-caller-identity --profile iot-dev`. Credentials remain in your local AWS configuration.

## Package, plan, and apply

From the repository root:

```sh
python cloud/lambda/package.py
cd infra/terraform
terraform init
terraform fmt -check -recursive .
terraform validate
terraform plan -var='aws_region=us-east-1' -var='environment=dev' -out=tfplan
```

Review the plan and confirm the AWS account and region before creating resources. When ready, apply the reviewed plan explicitly:

```sh
terraform apply tfplan
terraform output
```

For profile selection, set `AWS_PROFILE=iot-dev` in the shell before Terraform. Never put credentials in `.tfvars`. The current backend uses local Terraform state; configure an encrypted remote backend with locking before team/shared use. Securely back up state because it records resource metadata.

## Device connectivity

After provisioning, create a unique AWS IoT Thing and certificate per device, then attach a policy constrained to its own client ID and topic paths. At minimum, allow `iot:Connect` for the device client ID and `iot:Publish` only to its telemetry and status topics. Add subscribe/receive permissions only if the device implements commands. Obtain the AWS IoT endpoint and root CA, and provision certificate/private key material securely on the device; never commit it.

## Cleanup

To remove the dev resources, verify the target account and inspect `terraform plan -destroy`, then run `terraform destroy` only when you intend to delete the table and related resources. DynamoDB data will be deleted with the table. Export any data you need first.
