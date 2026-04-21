@echo off
setlocal EnableDelayedExpansion

echo ============================================
echo   CS2 Price Scraper + Trading Bot
echo ============================================
echo.

REM Check for virtual environment
if exist venv\Scripts\activate.bat (
    echo [1/4] Activating virtual environment...
    call venv\Scripts\activate.bat
) else (
    echo [1/4] No venv found. Using system Python.
    echo         Run setup.bat first if you encounter issues.
)

REM Ensure data directory exists
if not exist data mkdir data

echo [2/4] Starting FastAPI server + Trading Bot...
start "CS2 Server + Bot" python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

echo [3/4] Waiting for server to start...
timeout /t 4 /nobreak >nul

echo [4/4] Opening Trading Bot UI...
start http://localhost:8000/bot

echo.
echo ============================================
echo   All systems running!
echo.
echo   Bot UI:     http://localhost:8000/bot
echo   Search:     http://localhost:8000/search
echo   API Docs:   http://localhost:8000/api/docs
echo   Dashboard:  http://localhost:8000/dashboard
echo.
echo   Close this window to stop everything.
echo ============================================
echo.

REM Keep window open, stop server on close
echo Press any key to stop the server and bot...
pause >nul

echo.
echo Stopping server and bot...
taskkill /F /FI "WINDOWTITLE eq CS2 Server + Bot" >nul 2>&1
echo Done.
