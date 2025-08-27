# CI/CD

This repository uses a GitHub Actions workflow for safe staging→production deployments.

A separate `gitleaks` workflow scans for committed secrets on every push and pull request.

Bandit, pip-audit, and ruff workflows run on every push and pull request to block risky code and dependencies.

A `trivy` workflow builds the API and worker images and fails if any HIGH or CRITICAL vulnerabilities are found, caching the vulnerability database for faster scans.

A nightly `pdf-smoke` workflow renders sample invoice and KOT PDFs for the demo tenant, asserting 200 responses within two seconds and uploading the outputs as build artifacts.

A `lighthouse-ci` workflow audits /guest, /admin, and /kds against LCP, INP, transfer size, and script size budgets, uploading HTML reports and failing the build if limits are exceeded.

1. **build-and-push** – builds the API image and pushes it to GitHub Container Registry (GHCR) tagged as `neo-api:latest`.
2. **deploy-staging** – upgrades the staging environment via Helm, scrubs restored data to purge real PII (fakes names, phones, and emails; clears payment UTRs; rotates table/room/counter QR tokens), audits environment examples, runs `/api/admin/preflight`, smoke and canary probes, `pa11y-ci`, and Playwright smoke tests.
3. **manual-approval** – requires a human reviewer before production rollout.
4. **deploy-prod** – performs a blue/green deployment, repeats preflight and smoke/canary checks, and automatically rolls back on failure.

KUBE_CONFIG_* secrets are required for cluster access. An IAM role (`GitHubActionsECR`) trusts GitHub's `token.actions.githubusercontent.com` OIDC provider and grants the ECR permissions needed to push API and worker images. Workflows assume this role via `aws-actions/configure-aws-credentials@v2`, so no AWS access keys are stored.
