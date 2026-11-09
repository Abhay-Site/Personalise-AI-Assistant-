@echo off
echo ========================================================
echo   Starting ORBIT 180 (Backend + Frontend)
echo ========================================================

:: 1. Launch Backend in its own window
start "ORBIT 180 Backend" cmd /k "cd /d D:\orbit180\backend && .\venv\Scripts\python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"

:: 2. Launch Frontend in its own window
start "ORBIT 180 Frontend" cmd /k "cd /d D:\orbit180\frontend && npm.cmd run dev"

echo Both servers are now running in the background!
echo - Frontend: http://localhost:3000
echo - Backend:  http://127.0.0.1:8000
echo ========================================================
pause
