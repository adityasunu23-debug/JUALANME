@echo off
REM Double-click to start the Telegram bot (Windows).
REM Requires backend\.venv and BOT_TOKEN in backend\.env

setlocal
cd /d "%~dp0backend"

if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] Python venv not found.
  echo   1. Open a terminal in the backend folder
  echo   2. python -m venv .venv
  echo   3. .venv\Scripts\python.exe -m pip install -r requirements.txt
  pause
  exit /b 1
)

echo Starting Telegram bot... (press Ctrl+C to stop)
.venv\Scripts\python.exe -m app.bot.run

if errorlevel 1 pause
endlocal
