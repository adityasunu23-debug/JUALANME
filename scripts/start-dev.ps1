# Start the API (uvicorn) and the Next.js dashboard in two separate windows.
# Usage:  powershell -ExecutionPolicy Bypass -File scripts\start-dev.ps1
# Stop:   close the two windows, or run scripts\stop-dev.ps1

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root "backend"
$dashboard = Join-Path $root "dashboard"
$python = Join-Path $backend ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    Write-Host "Python venv not found at backend\.venv" -ForegroundColor Yellow
    Write-Host "  cd backend"
    Write-Host "  python -m venv .venv"
    Write-Host "  .\.venv\Scripts\python.exe -m pip install -r requirements.txt"
    exit 1
}

if (-not (Test-Path (Join-Path $dashboard "node_modules"))) {
    Write-Host "dashboard\node_modules not found - run: cd dashboard && npm install" -ForegroundColor Yellow
    exit 1
}

$apiArgs = @(
    "-NoExit",
    "-Command",
    "Set-Location '$backend'; & '$python' -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
)
Start-Process -FilePath "powershell.exe" -ArgumentList $apiArgs -WindowStyle Normal

$uiArgs = @(
    "-NoExit",
    "-Command",
    "Set-Location '$dashboard'; npm run dev"
)
Start-Process -FilePath "powershell.exe" -ArgumentList $uiArgs -WindowStyle Normal

Write-Host "Started API      -> http://127.0.0.1:8000 (docs: /docs)" -ForegroundColor Green
Write-Host "Started dashboard-> http://localhost:3000" -ForegroundColor Green
Write-Host "Wait ~10 seconds for both to boot, then open http://localhost:3000/login"
