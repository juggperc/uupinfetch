@echo off
echo ==================================
echo CS2 Price Scraper - Setup
echo ==================================

python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is required
    exit /b 1
)

if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Installing dependencies...
pip install -q --upgrade pip
pip install -q -r requirements.txt

if not exist data mkdir data

echo.
echo Setup complete!
echo.
echo To start the server, run:
echo   start.bat
echo.
echo Or manually:
echo   venv\Scripts\activate.bat
echo   uvicorn app.main:app --reload
echo.
pause
