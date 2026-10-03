#!/usr/bin/env bash
set -euo pipefail
scenario="${1:?Usage: incident.sh latency|postgres|redis|nginx|resources|recover}"
case "$scenario" in
  latency)
    python3 scripts/set-latency.py 1
    docker compose up -d --no-deps --force-recreate backend
    ;;
  postgres) docker compose --profile incidents up -d db-exhaust ;;
  redis) docker compose stop redis ;;
  nginx) docker compose stop backend ;;
  resources) docker compose --profile incidents up -d resource-pressure ;;
  recover)
    python3 scripts/set-latency.py 0
    docker compose --profile incidents stop db-exhaust resource-pressure
    docker compose start redis
    docker compose up -d --no-deps --force-recreate backend
    python3 scripts/smoke.py
    ;;
  *) echo 'Unknown scenario' >&2; exit 2 ;;
esac
