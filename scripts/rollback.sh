#!/usr/bin/env sh
# ============================================================================
# scripts/rollback.sh — redeploy the previous image tag
#
# If you pushed images to a registry (REGISTRY + IMAGE_BACKEND/IMAGE_DASHBOARD
# in .env), this re-tags the currently-running container image as :current and
# brings the stack back with it — a true rollback of the last deploy.
#
# Otherwise (local build only), the safe fallback is a full stop+rebuild from
# whatever code is checked out now; to roll back CODE you must checkout the
# previous git commit BEFORE running this script, e.g.:
#   git log --oneline -5
#   git checkout <prev-commit-sha> && bash scripts/rollback.sh
#
# Usage: bash scripts/rollback.sh
# ============================================================================
set -eu

cd "$(dirname "$0")/.."

# shellcheck disable=SC1091
[ -f .env ] && . ./.env

REGISTRY="${REGISTRY:-}"
IMAGE_BACKEND="${IMAGE_BACKEND:-backend}"
IMAGE_DASHBOARD="${IMAGE_DASHBOARD:-dashboard}"

if [ -n "$REGISTRY" ]; then
    echo "==> Registry mode: ${REGISTRY}"
    # Determine the image that was running successfully *before* this deploy.
    # Convention: deploys are tagged GIT sha; "current" is the live one.
    PREV_BACKEND=$(docker inspect --format '{{index .Config.Image}}' \
        "$(docker compose ps -q backend)" 2>/dev/null || echo "")
    PREV_DASH=$(docker inspect --format '{{index .Config.Image}}' \
        "$(docker compose ps -q dashboard)" 2>/dev/null || echo "")
    if [ -n "$PREV_BACKEND" ]; then
        echo "==> Rolling backend back to: $PREV_BACKEND"
        docker compose stop backend
        docker tag "$PREV_BACKEND" "${REGISTRY}/${IMAGE_BACKEND}:rollback-target" 2>/dev/null || true
        BACKEND_IMAGE="${PREV_BACKEND}" docker compose up -d --no-deps backend || true
    else
        echo "==> No running backend container found; pulling last known good tag."
        docker pull "${REGISTRY}/${IMAGE_BACKEND}:previous" || true
    fi
    if [ -n "$PREV_DASH" ]; then
        echo "==> Rolling dashboard back to: $PREV_DASH"
        docker compose stop dashboard
        docker tag "$PREV_DASH" "${REGISTRY}/${IMAGE_DASHBOARD}:rollback-target" 2>/dev/null || true
        DASHBOARD_IMAGE="${PREV_DASH}" docker compose up -d --no-deps dashboard || true
    fi
    echo "==> Done. Verify:  docker compose ps"
else
    echo "==> No REGISTRY configured — local rebuild fallback."
    echo "    (To roll back source code, checkout the previous git commit first.)"
    docker compose down
    docker compose up -d --build
    echo "==> Done. Verify:  docker compose ps"
fi
