# AWS deployment

The Terraform stack provisions an ingestion foundation (AWS IoT telemetry rule, Lambda, DynamoDB, IAM, and CloudWatch) plus a private S3 bucket and CloudFront distribution for the static dashboard. **No AWS resources have been deployed from this repository.** ECS/Fargate and an AWS-backed API read adapter are not included.

## Prerequisites

- An AWS account and IAM Identity Center/assumed role or other short-lived credentials with permissions for the resources shown by Terraform.
- AWS CLI, Terraform >= 1.6, Python 3, Node.js/npm, and PowerShell.
- Use a dedicated dev account or region first. Do not paste AWS access keys into chat or commit them to the repo.

Authenticate locally with your approved method (for example `aws sso login --profile iot-dev`) and verify identity using `aws sts get-caller-identity --profile iot-dev`.

## Provision infrastructure

From the repository root:

```sh
python cloud/lambda/package.py
cd infra/terraform
terraform init
terraform fmt -check -recursive .
terraform validate
terraform plan -var='aws_region=us-east-1' -var='environment=dev' -out=tfplan
```

Review the plan, account, region, S3 bucket name, and estimated costs. Then explicitly apply the reviewed plan:

```sh
terraform apply tfplan
terraform output
```

Terraform outputs include `dashboard_url`, `dashboard_bucket_name`, and `cloudfront_distribution_id`. The CloudFront default certificate provides an HTTPS URL without requiring a custom domain. A custom domain and ACM certificate can be added later.

## Publish the dashboard

The website is a static React build. It needs a publicly reachable FastAPI URL; the API is **not** provisioned by this Terraform stack. Configure that service's CORS allowlist to include the CloudFront URL.

In PowerShell, from the repository root (replace values with Terraform outputs):

```powershell
./scripts/deploy-frontend.ps1 -ApiUrl "https://your-api.example.com" -BucketName "terraform-output-bucket" -DistributionId "terraform-output-id" -AwsProfile "iot-dev"
```

The script builds the frontend with the provided API URL, uploads the build to the private S3 bucket, and invalidates CloudFront. It uses `aws s3 sync --delete` only against the bucket name passed to it.

## Device connectivity

After provisioning, create a unique AWS IoT Thing and certificate per device, then attach a policy constrained to its own client ID and topic paths. At minimum, allow `iot:Connect` for the device client ID and `iot:Publish` only to its telemetry and status topics. Add subscribe/receive permissions only if the device implements commands. Obtain the AWS IoT endpoint and root CA, and provision certificate/private key material securely on the device; never commit it.

## Credentials, state, and cleanup

Set `AWS_PROFILE=iot-dev` before Terraform or use the profile option with AWS CLI. Never put credentials in `.tfvars`. Terraform currently uses local state; configure encrypted remote state with locking before team/shared use, and protect state because it records resource metadata.

To remove the dev stack, confirm the AWS account and inspect `terraform plan -destroy`, then run `terraform destroy` only when you intend to delete the distribution, bucket, table, and related resources. The S3 bucket must be empty before it can be deleted. DynamoDB data is deleted with its table; export anything you need first.
