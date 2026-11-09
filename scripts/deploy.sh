#!/usr/bin/env sh
# ============================================================================
# scripts/deploy.sh — build & (re)deploy the production stack
# Usage (on the VPS):  bash scripts/deploy.sh
# REQUIRES: docker >= 20.10 with the compose v2 plugin.
# NOTE for Windows authors: chmod +x scripts/*.sh  on the Linux server, e.g.:
#   chmod +x scripts/*.sh
# ============================================================================
set -eu

cd "$(dirname "$0")/.."

if ! command -v docker >/dev/null 2>&1; then
    echo "ERROR: docker not found. Install docker engine + compose plugin." >&2
    exit 1
fi

if [ ! -f .env ]; then
    echo "ERROR: .env not found. Run: cp .env.example .env  and fill in secrets." >&2
    exit 1
fi

echo "==> Pulling latest base images..."
docker compose pull --ignore-buildable || true

echo "==> Stopping previous stack (keeping volumes)..."
docker compose down --remove-orphans || true

echo "==> Building & starting stack..."
docker compose up -d --build

echo "==> Waiting for services to become healthy..."
ATTEMPTS=0
MAX_ATTEMPTS=60
while [ "$ATTEMPTS" -lt "$MAX_ATTEMPTS" ]; do
    UNHEALTHY=$(docker compose ps --format '{{.Name}} {{.Health}}' \
        | awk '$2 == "starting" || $2 == "unhealthy" {print $1}')
    COUNT=$(echo "$UNHEALTHY" | grep -c . || true)
    if [ "$COUNT" -eq 0 ]; then
        break
    fi
    ATTEMPTS=$((ATTEMPTS + 1))
    echo "    waiting... ($ATTEMPTS/$MAX_ATTEMPTS)"
    sleep 5
done

if [ "$ATTEMPTS" -eq "$MAX_ATTEMPTS" ]; then
    echo "WARNING: some services still not healthy after $MAX_ATTEMPTS tries:" >&2
    docker compose ps >&2
    echo "    Check logs:  docker compose logs -f backend" >&2
    exit 2
fi
if [ "$ATTEMPTS" -eq "$MAX_ATTEMPTS" ]; then
    echo "WARNING: services still unhealthy after $MAX_ATTEMPTS tries." >&2
    exit 2
fi

echo "==> Tail of backend logs:"
docker compose logs --tail="20" backend || true

echo "==> Deploy OK. Backend on :8000, dashboard on :3000 via nginx :80."
