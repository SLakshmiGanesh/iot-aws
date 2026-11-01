# Testing strategy

## Existing automated checks

GitHub Actions currently runs:

- FastAPI backend tests.
- AWS Lambda handler tests.
- Terraform format, initialization, and validation.
- Frontend TypeScript build.
- Firmware compile and Docker build.

## Local commands

Backend:

```sh
cd backend
pip install -r requirements.txt pytest httpx
PYTHONPATH=. pytest -q
```

Lambda:

```sh
pip install -r cloud/lambda/requirements.txt pytest
python -m compileall -q cloud/lambda
python -m pytest -q cloud/lambda/tests
```

Frontend:

```sh
cd frontend
npm install
npm run build
npm test -- --run
```

Terraform:

```sh
terraform -chdir=infra/terraform fmt -check -recursive
terraform -chdir=infra/terraform init -backend=false
terraform -chdir=infra/terraform validate
```

## Coverage priorities

Add tests for isolated temporary SQLite databases, API pagination tokens, time-range edge cases, tenant isolation, DynamoDB conditional failures, retryable AWS errors, alert GSI pagination, and status-event ordering. Add frontend rendering and request-failure tests. Test firmware builds against placeholder configuration and separately validate secure device provisioning against a dedicated AWS test account.

Do not interpret unit tests or Terraform validation as proof of a production deployment. Real AWS integration tests require an isolated account, explicit budget controls, and a reviewed plan.
