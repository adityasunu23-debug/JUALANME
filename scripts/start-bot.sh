#!/usr/bin/env bash
# Start the Telegram bot in long-polling mode (Linux / macOS).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND="$ROOT/backend"

if [ ! -f "$BACKEND/.env" ]; then
  echo "backend/.env not found. Copy .env.example and set BOT_TOKEN first." >&2
  exit 1
fi

TOKEN="$(grep -E '^\s*BOT_TOKEN\s*=' "$BACKEND/.env" | head -n1 | cut -d= -f2- | tr -d '[:space:]"')"
if [ -z "${TOKEN}" ]; then
  echo "BOT_TOKEN is empty in backend/.env" >&2
  echo "  1. Open @BotFather in Telegram -> /newbot" >&2
  echo "  2. Put the token into backend/.env as BOT_TOKEN=<token>" >&2
  exit 1
fi

cd "$BACKEND"

if [ -x ".venv/bin/python" ]; then
  PY=".venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PY="python3"
else
  PY="python"
fi

echo "Starting Telegram bot (long polling) with $PY ..."
exec "$PY" -m app.bot.run
