.PHONY: up down incident-start incident-resolve
.PHONY: pilot

# Start the local development stack
up:
	docker-compose up --build

# Stop and remove containers, networks and volumes
down:
	docker-compose down --volumes --remove-orphans

incident-start:
        STATUS_API_URL=$(STATUS_API_URL) STATUS_API_TOKEN=$(STATUS_API_TOKEN) \
        python scripts/status_page.py start "$(TITLE)" "$(DETAILS)"

incident-resolve:
        STATUS_API_URL=$(STATUS_API_URL) STATUS_API_TOKEN=$(STATUS_API_TOKEN) \
        python scripts/status_page.py resolve "$(TITLE)"

# Tag release candidate and exercise pilot rollout on staging.
# Enable telemetry/NPS flags in a follow-up step.
pilot:
        python scripts/release_tag.py --rc
        python scripts/deploy_blue_green.py --env=staging
        python scripts/weighted_canary_ramp.py --env=staging
        python scripts/canary_probe.py --env=staging
        # enable telemetry/NPS flags here
