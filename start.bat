@echo off
REM ─────────────────────────────────────────────────────────────────────────────
REM  CRM Sequence Automator — Windows Start Script
REM  Starts the FastAPI backend + React frontend in two separate windows.
REM  Run this from the CRM root folder: c:\Users\abc\Downloads\CRM\CRM
REM ─────────────────────────────────────────────────────────────────────────────

echo.
echo  ╔══════════════════════════════════════════════════════╗
echo  ║       CRM Sequence Automator — Starting Up           ║
echo  ╚══════════════════════════════════════════════════════╝
echo.

REM Check venv exists
if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found.
    echo Run: python -m venv venv ^&^& venv\Scripts\activate ^&^& pip install -r backend\requirements.txt
    pause
    exit /b 1
)

REM Check .env exists
if not exist ".env" (
    echo [ERROR] .env file not found.
    echo Copy .env.example to .env and fill in your credentials.
    pause
    exit /b 1
)

REM Check node_modules
if not exist "frontend\dashboard\node_modules" (
    echo [INFO] Installing frontend dependencies...
    cd frontend\dashboard
    call npm install
    cd ..\..
)

echo [1/2] Starting FastAPI backend on http://localhost:8000 ...
start "CRM Backend" cmd /k "venv\Scripts\activate && venv\Scripts\uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload"

REM Small delay so backend starts first
timeout /t 3 /nobreak >nul

echo [2/2] Starting React frontend on http://localhost:5173 ...
start "CRM Frontend" cmd /k "cd frontend\dashboard && npm run dev"

echo.
echo  ✅ Both servers are starting up.
echo.
echo  Backend API:   http://localhost:8000
echo  API Docs:      http://localhost:8000/docs
echo  Dashboard:     http://localhost:5173
echo.
echo  Close the two terminal windows to stop the servers.
echo.
pause
