#!/bin/bash
set -e

echo "==========================================="
echo "   CS2 Price Scraper - Easy Launch"
echo "==========================================="
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] python3 is not installed."
    echo "Please install Python 3.10+ using your package manager."
    exit 1
fi

# Ensure data dir exists
mkdir -p data

# Create venv if missing
if [ ! -d "venv" ]; then
    echo "[1/3] Creating virtual environment..."
    python3 -m venv venv
fi

# Activate venv
source venv/bin/activate

# Install / update deps
echo "[2/3] Checking dependencies..."
pip install -q -r requirements.txt

# Start server
echo "[3/3] Starting server..."
echo ""
echo "The bot UI will open automatically in your browser."
echo "Press Ctrl+C to stop the server."
echo ""

# Open browser after a short delay (macOS vs Linux)
(
    sleep 3
    if command -v xdg-open &> /dev/null; then
        xdg-open "http://127.0.0.1:8000/bot" &> /dev/null || true
    elif command -v open &> /dev/null; then
        open "http://127.0.0.1:8000/bot" &> /dev/null || true
    fi
) &

# Run server
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
