@echo off
echo ========================================================
echo   Starting Personal AI Assistant (Backend + Frontend)
echo ========================================================

:: 1. Launch Backend in its own window
start "Personal AI Assistant Backend" cmd /k "cd /d "%~dp0backend" && .\venv\Scripts\python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"

:: 2. Launch Frontend in its own window
start "Personal AI Assistant Frontend" cmd /k "cd /d "%~dp0frontend" && npm.cmd run dev"

echo Both servers are now running in the background!
echo - Frontend: http://localhost:3000
echo - Backend:  http://127.0.0.1:8000
echo ========================================================
pause
