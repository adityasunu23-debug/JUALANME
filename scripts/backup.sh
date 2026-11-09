#!/usr/bin/env sh
# ============================================================================
# scripts/backup.sh — dump the PostgreSQL database to ./backups
#
# Usage:
#   bash scripts/backup.sh              # one-off dump
#   (cron) 0 3 * * * cd /opt/store && bash scripts/backup.sh >> backups/cron.log 2>&1
#
# Restoring backups/keep bleeding: ./backups is mounted under ./backend/data
# — move/copy files there so they are retrievable from the host machine:
# the volume ./backend/data:/app/data also contains them if you later want the
# bot to serve a dump to an OWNER via Telegram.
# ============================================================================
set -eu

cd "$(dirname "$0")/.."

# shellcheck disable=SC1091
[ -f .env ] && . ./.env

POSTGRES_USER="${POSTGRES_USER:-store}"
POSTGRES_DB="${POSTGRES_DB:-store_db}"
TS=$(date -u +"%Y%m%dT%H%M%SZ")

OUT_DIR="./backups"
BACKEND_DATA_DIR="./backend/data/backups"
mkdir -p "$OUT_DIR" "$BACKEND_DATA_DIR"

if ! docker compose ps --status running postgres >/dev/null 2>&1; then
    echo "ERROR: postgres container is not running. Start the stack first." >&2
    exit 1
fi

DUMP_FILE="$OUT_DIR/${POSTGRES_DB}_${TS}.sql.gz"

echo "==> Dumping database '$POSTGRES_DB' to $DUMP_FILE ..."
docker compose exec -T postgres \
    pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner --clean --if-exists \
    | gzip > "$DUMP_FILE"

# Also keep a copy inside the mounted volume -> retrievable from backend/data
cp "$DUMP_FILE" "$BACKEND_DATA_DIR/"

LINES=$(gzip -l "$DUMP_FILE" | awk 'NR==2{print $2}')
echo "==> OK: $DUMP_FILE ($LINES bytes uncompressed)"

# Rotate: keep the 14 newest dumps
ls -1t "$OUT_DIR"/${POSTGRES_DB}_*.sql.gz 2>/dev/null | tail -n +15 | while IFS= read -r old; do
    echo "    pruning $old"
    rm -f "$old"
done

# Retrievable: scp the file off the VPS, e.g.
#   scp user@your-vps:/opt/store/backups/${POSTGRES_DB}_${TS}.sql.gz ./local-backups/
