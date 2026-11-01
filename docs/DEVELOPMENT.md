# Development

## Local setup

Start the demo from the repository root with Docker Compose:

```sh
docker compose up --build
```

The React dashboard is available at `http://localhost:5173`; FastAPI and its OpenAPI page are at `http://localhost:8000` and `/docs`. Local mode uses SQLite and synthetic readings. It does not need AWS credentials.

For backend development, install the dependencies and tests, then run:

```sh
cd backend
pip install -r requirements.txt pytest httpx ruff
PYTHONPATH=. pytest -q
ruff check --select E4,E7,E9,F . ../cloud/lambda
```

Frontend:

```sh
cd frontend
npm install
npm run build
npm test
```

Firmware requires PlatformIO. Keep `firmware/include/config.h` local and untracked; the example header contains placeholders:

```sh
pio run -d firmware
```

Terraform validation is available without AWS credentials:

```sh
terraform fmt -check -recursive infra/terraform
terraform -chdir=infra/terraform init -backend=false
terraform -chdir=infra/terraform validate
```

## Pull requests and branch protection

CI runs backend tests and lint, Lambda tests, Terraform format/validate, frontend build/tests, firmware compilation, and Docker builds. Configure the repository's default branch to require these status checks before merge. Also require pull-request review, dismiss stale approvals after new commits, block force pushes and branch deletion, and enable secret scanning and dependency alerts where available.

CI checks source code; it does not deploy AWS resources. Deployment requires a short-lived operator identity and a reviewed Terraform plan.
