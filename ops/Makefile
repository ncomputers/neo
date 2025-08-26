.PHONY: up down incident-start incident-resolve
.PHONY: pilot

# Start the local development stack
up:
	docker-compose up --build

# Stop and remove containers, networks and volumes
down:
	docker-compose down --volumes --remove-orphans

incident-start:
	python scripts/status_page.py start "$(TITLE)" "$(DETAILS)"

incident-resolve:
        python scripts/status_page.py resolve "$(TITLE)"

# Deploy pilot stack, ramp traffic, and enable telemetry.
# Requires TELEMETRY_API_URL and TELEMETRY_API_TOKEN.
pilot:
	python scripts/deploy_blue_green.py --env=pilot
	python scripts/weighted_canary_ramp.py --env=pilot
	curl -X POST "$${TELEMETRY_API_URL}/enable?env=pilot" -H "Authorization: Bearer $${TELEMETRY_API_TOKEN}"
