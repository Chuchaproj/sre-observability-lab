.PHONY: init install test lint up down smoke load recover
init:
	python3 scripts/init-env.py
install:
	python3 -m venv .venv
	.venv/bin/pip install -r requirements-dev.txt
test:
	.venv/bin/python -m pytest -q
lint:
	.venv/bin/ruff check app tests scripts
	shellcheck scripts/*.sh
	yamllint -c .yamllint compose.yaml monitoring .github
	hadolint Dockerfile
up:
	docker compose up -d --build --wait --wait-timeout 240
down:
	docker compose --profile incidents down
smoke:
	python3 scripts/smoke.py
load:
	docker compose --profile load run --rm load
recover:
	bash scripts/incident.sh recover

.PHONY: secrets
secrets:
	bash scripts/check-secrets.sh
