.PHONY: up down incident-start incident-resolve

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
