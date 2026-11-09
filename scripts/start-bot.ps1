# Start the Telegram bot in long-polling mode (Windows / PowerShell).
# Usage:  powershell -ExecutionPolicy Bypass -File scripts\start-bot.ps1

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root "backend"
$python = Join-Path $backend ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    Write-Host "Python venv not found. Create it first:" -ForegroundColor Yellow
    Write-Host "  cd backend"
    Write-Host "  python -m venv .venv"
    Write-Host "  .\.venv\Scripts\python.exe -m pip install -r requirements.txt"
    exit 1
}

$envFile = Join-Path $backend ".env"
if (-not (Test-Path $envFile)) {
    Write-Host "backend\.env not found. Copy .env.example and fill in BOT_TOKEN." -ForegroundColor Yellow
    exit 1
}

$token = Select-String -Path $envFile -Pattern '^\s*BOT_TOKEN\s*=\s*(.+)$' |
    ForEach-Object { $_.Matches[0].Groups[1].Value.Trim() } |
    Select-Object -First 1

if ([string]::IsNullOrWhiteSpace($token)) {
    Write-Host "BOT_TOKEN is empty in backend\.env" -ForegroundColor Yellow
    Write-Host "  1. Open @BotFather in Telegram -> /newbot"
    Write-Host "  2. Copy the token into backend\.env as BOT_TOKEN=<token>"
    exit 1
}

Write-Host "Starting Telegram bot (long polling)..." -ForegroundColor Green
Set-Location $backend
& $python -m app.bot.run
