.PHONY: release-rc stage pilot release-ga prod analyze-hot

release-rc:
	python scripts/release_tag.py --rc

stage:
	python scripts/deploy_blue_green.py --env=staging
	python scripts/canary_probe.py --env=staging
	python scripts/weighted_canary_ramp.py --env=staging --steps "5,25,50,100"

pilot: release-rc stage
	python scripts/emit_test_alert.py --env=staging
	pytest -q
	npx playwright test
	python scripts/pdf_smoke.py --env=staging
	bash scripts/backup_smoke.sh

release-ga:
	python scripts/release_tag.py --ga

prod:
        python scripts/deploy_blue_green.py --env=prod
        python scripts/weighted_canary_ramp.py --env=prod --steps "5,25,50,100"

analyze-hot:
        python scripts/auto_analyze_hot_tables.py
