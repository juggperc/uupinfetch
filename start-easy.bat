@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

title CS2 Price Scraper - Easy Launcher
echo ===========================================
echo   CS2 Price Scraper - Easy Launch
echo ===========================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.10+ from https://python.org
    pause
    exit /b 1
)

:: Ensure data dir exists
if not exist "data" mkdir data

:: Create venv if missing
if not exist "venv" (
    echo [1/3] Creating virtual environment...
    python -m venv venv
)

:: Activate venv
call venv\Scripts\activate.bat

:: Install / update deps
echo [2/3] Checking dependencies...
pip install -q -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

:: Start server in background
echo [3/3] Starting server...
echo.
echo The bot UI will open automatically in your browser.
echo Press Ctrl+C here to stop the server.
echo.

:: Open browser after a short delay
start /b cmd /c "timeout /t 3 >nul && start http://127.0.0.1:8000/bot"

:: Run server
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

:: Keep window open on crash
pause
