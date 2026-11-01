# AWS deployment

The Terraform stack provisions AWS IoT telemetry routing, Lambda processing, DynamoDB telemetry and device registry tables, a rate-limited read-only API Gateway HTTP API, IAM, CloudWatch logs and alarms, bounded Lambda retries with an encrypted SQS failure queue, and a private S3 + CloudFront dashboard. **No AWS resources have been deployed from this repository.** ECS/Fargate is not included.

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

Terraform outputs include `dashboard_url`, `api_url`, `dashboard_bucket_name`, `cloudfront_distribution_id`, and the generated IoT policy name. Telemetry expires after 90 days by default; set `telemetry_retention_days` in the Terraform plan to adjust it. CloudWatch Lambda error/throttle and SQS backlog alarms are created without notification targets. Lambda asynchronous failures retry up to two times within one hour, then enter the encrypted 14-day SQS failure queue; inspect and redrive messages manually after resolving the cause. The CloudFront default certificate provides an HTTPS URL without requiring a custom domain. A custom domain and ACM certificate can be added later.

## Publish the dashboard

The website is a static React build. Terraform provisions a public, read-only API Gateway HTTP API backed by a Lambda reader and DynamoDB. API CORS is restricted to the CloudFront origin. The dashboard build receives the API URL from Terraform.

For AWS CloudShell, from the repository root after Terraform apply:

```bash
API_URL=$(terraform -chdir=infra/terraform output -raw api_url)
BUCKET=$(terraform -chdir=infra/terraform output -raw dashboard_bucket_name)
DIST_ID=$(terraform -chdir=infra/terraform output -raw cloudfront_distribution_id)
cd frontend
npm install
VITE_API_URL="$API_URL" npm run build
cd ..
aws s3 sync frontend/dist "s3://$BUCKET/" --delete
aws cloudfront create-invalidation --distribution-id "$DIST_ID" --paths "/*"
terraform -chdir=infra/terraform output -raw dashboard_url
```

The Windows helper `scripts/deploy-frontend.ps1` performs the same build, upload, and invalidation when passed `-ApiUrl`, `-BucketName`, and `-DistributionId`. Both upload methods delete old objects only in the specified dashboard bucket.

## Device connectivity

Terraform creates the least-privilege `iot_device_policy_name` output. Create a unique AWS IoT Thing and certificate per device, set its `home_id` Thing attribute to the configured home ID, and attach this policy to the certificate. The certificate must also be attached to the Thing for the policy Thing variables to resolve. The policy permits connect for that Thing and publish only to its telemetry/status topic paths. Obtain the AWS IoT endpoint and root CA, and provision certificate/private key material securely on the device; never commit it.

## Credentials, state, and cleanup

Set `AWS_PROFILE=iot-dev` before Terraform or use the profile option with AWS CLI. Never put credentials in `.tfvars`. Terraform currently uses local state; configure encrypted remote state with locking before team/shared use, and protect state because it records resource metadata.

To remove the dev stack, confirm the AWS account and inspect `terraform plan -destroy`, then run `terraform destroy` only when you intend to delete the distribution, bucket, table, and related resources. The S3 bucket must be empty before it can be deleted. DynamoDB data is deleted with its table; export anything you need first.
