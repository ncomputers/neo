# CI/CD

This repository uses a GitHub Actions workflow for safe staging→production deployments.

A separate `gitleaks` workflow scans for committed secrets on every push and pull request.

A nightly `pdf-smoke` workflow renders sample invoice and KOT PDFs for the demo tenant, asserting 200 responses within two seconds and uploading the outputs as build artifacts.

1. **build-and-push** – builds the API and worker images and pushes them to the registry tagged with the commit SHA.
2. **deploy-staging** – upgrades the staging environment via Helm, scrubs restored data to purge real PII (fakes names, phones, and emails; clears payment UTRs; rotates table/room/counter QR tokens), audits environment examples, runs `/api/admin/preflight`, smoke and canary probes, `pa11y-ci`, and Playwright smoke tests.
3. **manual-approval** – requires a human reviewer before production rollout.
4. **deploy-prod** – performs a blue/green deployment, repeats preflight and smoke/canary checks, and automatically rolls back on failure.

Secrets such as `REGISTRY_*` and `KUBE_CONFIG_*` are required for registry and cluster access.
